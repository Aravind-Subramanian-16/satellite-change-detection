import base64, io, re, zlib
from pathlib import Path
import pytest
pytest.importorskip("reportlab")
from PIL import Image
from reports import build_report


def _pdf_text(data: bytes) -> str:
    """Decode ReportLab's ASCII85+Flate content streams for text assertions."""
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        raw = match.group(1).strip()
        try:
            if raw.endswith(b"~>"):
                raw = base64.a85decode(raw, adobe=True)
            raw = zlib.decompress(raw)
        except Exception:
            continue
        chunks.append(raw.decode("latin-1", "replace"))
    return "\n".join(chunks)

def test_pdf_report_is_created(tmp_path):
    image=Image.new("RGB",(8,8)); buf=io.BytesIO(); image.save(buf,"PNG")
    result={"percent_changed":1.0,"image_a_base64":base64.b64encode(buf.getvalue()).decode(),"change_regions":[]}
    path=build_report(result,tmp_path/"report.pdf")
    assert path.read_bytes().startswith(b"%PDF")


def test_pdf_report_contains_method_provenance_and_unvalidated_badge(tmp_path):
    result = {
        "pipeline": "spectral",
        "profile": "agriculture",
        "percent_changed": 1.8,
        "percent_cloud_masked": 12.4,
        "validation_status": "unvalidated, qualitative only",
        "display_metrics": False,
        "thresholds": {"ndvi_drop": 0.15, "mmu_ha": 0.5},
        "date_before": "2025-05-01",
        "date_after": "2025-09-01",
        "scenes": {"before": {"id": "S2B_BEFORE_1"}, "after": {"id": "S2B_AFTER_1"}},
        "provenance": {
            "commit": "abc123def456",
            "scene_ids": ["S2B_BEFORE_1", "S2B_AFTER_1"],
            "dates": {"before": "2025-05-01", "after": "2025-09-01"},
            "percent_masked": 12.4,
            "timestamp_utc": "2026-10-21T00:00:00+00:00",
            "options": {"mmu_ha": 0.5},
        },
        "change_regions": [
            {"change_type": "Urban expansion", "area_ha": 12.0, "pixel_area": 1200, "confidence_label": "High"}
        ],
    }
    path = build_report(result, tmp_path / "report.pdf")
    text = _pdf_text(path.read_bytes())
    for needle in (
        "UNVALIDATED PROFILE",
        "no accuracy number is shown",
        "abc123def456",
        "S2B_BEFORE_1",
        "ndvi_drop",
        "mmu_ha",
        "12.40%",
        "Urban expansion",
        "Limitations",
        "Decision support only",
    ):
        assert needle in text, needle
