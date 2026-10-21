import base64
import io
import re
import zlib

import pytest

pytest.importorskip("reportlab")
from PIL import Image

from reports import build_report

FORBIDDEN = ("accurate", "ai-powered", "state of the art", "reliable")


def _pdf_text(data: bytes) -> str:
    """Decode ReportLab's ASCII85+Flate content streams for text assertions."""
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.DOTALL):
        raw = match.group(1).strip()
        try:
            if raw.endswith(b"~>"):
                raw = base64.a85decode(raw, adobe=True)
            raw = zlib.decompress(raw)
        except Exception:  # noqa: BLE001, S112 - streams that are not Flate text are skipped
            continue
        chunks.append(raw.decode("latin-1", "replace"))
    return "\n".join(chunks)


def _png_b64() -> str:
    image = Image.new("RGB", (8, 8), (30, 90, 30))
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _full_result() -> dict:
    return {
        "pipeline": "spectral",
        "profile": "agriculture",
        "profile_label": "Farmland",
        "percent_changed": 1.8,
        "percent_changed_valid": 2.1,
        "percent_cloud_masked": 12.4,
        "validation_status": "unvalidated, qualitative only",
        "display_metrics": False,
        "thresholds": {
            "profile": "agriculture",
            "mode": "profile",
            "thresholds": {"ndvi_drop": 0.15, "ndmi_drop": 0.12, "ndvi_gain": 0.15},
            "mmu": {"mmu_ha": 0.5, "min_pixels": 50, "removed_components": 3},
        },
        "date_before": "2025-05-01",
        "date_after": "2025-09-01",
        "resolved_place_name": "Test Valley",
        "scenes": {"before": {"id": "S2B_BEFORE_1"}, "after": {"id": "S2B_AFTER_1"}},
        "class_table": {
            "rows": [
                {"change_type": "Agricultural land conversion", "area_ha": 12.0, "area_m2": 120000.0,
                 "percent_of_aoi": 7.5, "region_count": 2},
                {"change_type": "Vegetation gain / reforestation", "area_ha": 3.25, "area_m2": 32500.0,
                 "percent_of_aoi": 2.03, "region_count": 1},
            ],
            "total": {"change_type": "Total", "area_ha": 15.25, "area_m2": 152500.0,
                      "percent_of_aoi": 9.53, "region_count": 3},
            "note": "Areas are counted once per patch; patches are the 20 largest.",
        },
        "change_regions": [
            {"change_type": "Agricultural land conversion", "area_ha": 12.0, "pixel_area": 1200,
             "confidence_label": "High"}
        ],
        "image_a_base64": _png_b64(),
        "image_b_base64": _png_b64(),
        "overlay_base64": _png_b64(),
        "mask_base64": _png_b64(),
        "provenance": {
            "commit": "abc123def456",
            "app_version": "0.9.0",
            "scene_ids": ["S2B_BEFORE_1", "S2B_AFTER_1"],
            "dates": {"before": "2025-05-01", "after": "2025-09-01"},
            "percent_masked": 12.4,
            "timestamp_utc": "2026-10-21T00:00:00+00:00",
            "options": {"mmu_ha": 0.5},
            "threshold_provenance": {
                "ndvi_gain": "chosen by developer, untested: mirrors ndvi_drop so greening and browning are treated symmetrically.",
            },
        },
        "profile_notes": ["Patches that became greener are reported separately."],
    }


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
        "Limitations",
        "Decision support only",
    ):
        assert needle in text, needle


def test_pdf_report_has_required_phase3_sections(tmp_path):
    path = build_report(_full_result(), tmp_path / "report.pdf")
    text = _pdf_text(path.read_bytes())
    for needle in (
        "Summary in plain language",
        "This report compares two images of Test Valley",
        "Legend",
        "red = pixels the rules flagged as changed",
        "white = pixels excluded from the statistics",
        "What we found, by type",
        "Agricultural land conversion",
        "Vegetation gain / reforestation",
        "Total",
        "Method and settings",
        "Greenness change threshold",
        "Where these numbers come from",
        "chosen by developer, untested",
        "Why this badge",
        "No labelled evaluation exists for this profile",
        "Data and credits",
        "contains modified Copernicus Sentinel data [2025]",
        "App version",
        "0.9.0",
        "Limitations",
        "Provenance",
    ):
        assert needle in text, needle


def test_pdf_report_matches_results_numbers(tmp_path):
    result = _full_result()
    path = build_report(result, tmp_path / "report.pdf")
    text = _pdf_text(path.read_bytes())
    assert "1.80%" in text
    for row in result["class_table"]["rows"]:
        assert f"{row['area_ha']:.2f}" in text
        assert f"{row['percent_of_aoi']:.2f}%" in text
    assert "15.25" in text
    assert "9.53%" in text
    # Same adaptive units as the on-screen table: 12 ha renders as "12.00 ha (29.7 acres)".
    assert "29.7 acres" in text
    assert "37.7 acres" in text


def test_pdf_report_has_no_forbidden_claims(tmp_path):
    path = build_report(_full_result(), tmp_path / "report.pdf")
    text = _pdf_text(path.read_bytes()).lower()
    for word in FORBIDDEN:
        assert word not in text, word
    cleaned = text.replace("unvalidated", "").replace("unvalidatedly", "")
    assert "validated" not in cleaned
    assert "accuracy" not in cleaned.replace("no accuracy number is shown", "")


def test_pdf_report_handles_missing_inputs_gracefully(tmp_path):
    path = build_report({}, tmp_path / "empty.pdf")
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    text = _pdf_text(data)
    assert "Satellite change analysis" in text
    assert "Summary in plain language" in text
    assert "Limitations" in text
