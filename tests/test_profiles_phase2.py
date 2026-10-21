"""Synthetic image-pair tests for the Phase 2 profile work: water profile,
agriculture gain split, per-region explanations, class tables and warnings.

Everything runs on synthetic index fields and encoded PNG rasters; no network,
no Copernicus, no test-split data.
"""
from __future__ import annotations

import numpy as np
import pytest

from change_reasoner import reason_regions
from exports import regions_to_csv, regions_to_geojson
from live_pipeline import build_class_table, profile_warnings
from profiles import get_profile, profile_public
from profiles.detection import (
    WATER_GAIN_LABEL,
    WATER_LOSS_LABEL,
    detect_profile,
    relabel_water_regions,
)
from profiles.explanations import TEMPLATES, explain_region
from spectral_pipeline import encode_indices

SHAPE = (40, 40)
PATCH = (slice(8, 20), slice(8, 20))


def _fields(**values):
    return {key: np.full(SHAPE, value, dtype=np.float32) for key, value in values.items()}


def _scene(ndvi=0.5, ndbi=0.0, nbr=0.3, ndmi=0.2, bsi=0.0, rgb=(90, 110, 80), scl=None):
    indices = _fields(ndvi=ndvi, ndbi=ndbi, nbr=nbr, ndmi=ndmi, bsi=bsi)
    rgb_arr = np.full(SHAPE + (3,), rgb, dtype=np.uint8)
    scl_arr = np.zeros(SHAPE, dtype=np.uint8) if scl is None else scl
    encoded = encode_indices(indices["ndvi"], indices["ndbi"], scl_arr)
    return {"indices": indices, "rgb": rgb_arr, "encoded": encoded, "scl": scl_arr}


def _run_profile(profile_key, before, after, **kwargs):
    before["encoded"] = encode_indices(before["indices"]["ndvi"], before["indices"]["ndbi"], before["scl"])
    after["encoded"] = encode_indices(after["indices"]["ndvi"], after["indices"]["ndbi"], after["scl"])
    mask, invalid, meta = detect_profile(
        before["indices"], after["indices"], get_profile(profile_key), scl_a=before.get("scl"),
        scl_b=after.get("scl"), pixel_area_m2=100.0, **kwargs,
    )
    regions = reason_regions(before["rgb"], after["rgb"], mask, idx_a=before["encoded"], idx_b=after["encoded"])
    for region in regions:
        region["area_m2"] = round(region["pixel_area"] * 100.0, 2)
        region["area_ha"] = round(region["area_m2"] / 10_000.0, 3)
    return mask, invalid, meta, regions


FORBIDDEN = ("accurate", "AI-powered", "state of the art", "reliable")


def _claim_free(text: str) -> None:
    for word in FORBIDDEN:
        assert word.lower() not in text.lower(), f"forbidden word {word!r} in: {text}"
    # "validated" may only appear as the honest "unvalidated" label.
    assert "validated" not in text.lower().replace("unvalidated", "")


# ── Water profile ────────────────────────────────────────────────────────────


def test_water_gain_patch_gets_right_label_and_area():
    before = _scene(ndvi=0.30, ndmi=0.15, rgb=(120, 105, 70))
    after = _scene(ndvi=0.30, ndmi=0.15, rgb=(120, 105, 70))
    after["indices"]["ndvi"][PATCH] = -0.30
    after["indices"]["ndmi"][PATCH] = -0.40
    after["rgb"][PATCH] = (12, 22, 34)
    mask, invalid, meta, regions = _run_profile("water", before, after)

    assert not invalid.any()
    assert meta["flags"]["water_gain_pixels"] == 144
    assert meta["flags"]["water_loss_pixels"] == 0
    assert mask[PATCH].all()
    relabel_water_regions(regions)
    assert regions and regions[0]["change_type"] == WATER_GAIN_LABEL
    assert regions[0]["pixel_area"] == 144
    assert regions[0]["area_ha"] == pytest.approx(1.44)


def test_water_loss_patch_gets_right_label_and_area():
    before = _scene(ndvi=0.30, ndmi=0.15, rgb=(120, 105, 70))
    before["indices"]["ndvi"][PATCH] = -0.35
    before["indices"]["ndmi"][PATCH] = -0.45
    before["rgb"][PATCH] = (10, 25, 40)
    after = _scene(ndvi=0.30, ndmi=0.15, rgb=(120, 105, 70))
    mask, _, meta, regions = _run_profile("water", before, after)

    assert meta["flags"]["water_loss_pixels"] == 144
    assert meta["flags"]["water_gain_pixels"] == 0
    assert mask[PATCH].all()
    relabel_water_regions(regions)
    assert regions and regions[0]["change_type"] == WATER_LOSS_LABEL


def test_water_profile_rejects_wet_soil():
    before = _scene(ndvi=0.30, ndmi=0.15)
    after = _scene(ndvi=0.30, ndmi=0.15)
    after["indices"]["ndvi"][PATCH] = 0.05   # damp but not water-like
    after["indices"]["ndmi"][PATCH] = -0.30
    mask, _, meta, _ = _run_profile("water", before, after)

    assert not mask.any()
    assert meta["flags"]["water_gain_pixels"] == 0


def test_water_profile_masks_cloud_shadow_mandatorily():
    before = _scene(ndvi=0.30, ndmi=0.15)
    after = _scene(ndvi=0.30, ndmi=0.15)
    after["indices"]["ndvi"][PATCH] = -0.30
    after["indices"]["ndmi"][PATCH] = -0.40
    scl = np.zeros(SHAPE, dtype=np.uint8)
    scl[8:20, 8:14] = 9   # cloud over half the new-water patch
    before["scl"] = scl
    after["scl"] = scl
    mask, invalid, meta, _ = _run_profile("water", before, after)

    assert invalid[8:20, 8:14].all()
    assert not mask[8:20, 8:14].any()
    assert mask[8:20, 14:20].all()   # clear half still detected
    assert meta["cloud_mask_enabled"] is True
    assert get_profile("water").cloud_mask_mandatory is True


def test_water_profile_mmu_discards_small_pond():
    before = _scene(ndvi=0.30, ndmi=0.15)
    after = _scene(ndvi=0.30, ndmi=0.15)
    after["indices"]["ndvi"][18:21, 18:21] = -0.35   # 9 px = 0.09 ha < 0.25 ha MMU
    after["indices"]["ndmi"][18:21, 18:21] = -0.45
    mask, _, meta, _ = _run_profile("water", before, after)

    assert not mask.any()
    assert meta["mmu"]["mmu_ha"] == 0.25


def test_water_profile_public_metadata_is_honest():
    public = profile_public("water")
    assert public["validation_status"] == "unvalidated, qualitative only"
    assert public["display_metrics"] is False
    assert public["threshold_provenance"]["water_ndvi_max"].startswith("chosen by developer, untested")
    assert "unvalidated" in public["validation_status"].lower()


# ── Agriculture gain split ───────────────────────────────────────────────────


def test_agriculture_gain_patch_flags_vegetation_gain():
    before = _scene(ndvi=0.40, ndmi=0.20, rgb=(110, 100, 60))
    after = _scene(ndvi=0.40, ndmi=0.20, rgb=(110, 100, 60))
    after["indices"]["ndvi"][PATCH] = 0.65
    after["rgb"][PATCH] = (40, 110, 50)
    mask, _, meta, regions = _run_profile("agriculture", before, after)

    assert meta["flags"]["vegetation_gain"] == 144
    assert meta["flags"]["vegetation_loss"] == 0
    assert mask[PATCH].all()
    assert regions and regions[0]["change_type"] == "Vegetation gain / reforestation"


def test_agriculture_loss_and_gain_are_split():
    before = _scene(ndvi=0.50, ndmi=0.20)
    after = _scene(ndvi=0.50, ndmi=0.20)
    after["indices"]["ndvi"][8:20, 8:20] = 0.20    # loss patch
    after["indices"]["ndvi"][22:30, 22:30] = 0.75  # gain patch
    mask, _, meta, _ = _run_profile("agriculture", before, after)

    assert mask[8:20, 8:20].all()
    assert mask[22:30, 22:30].all()
    assert meta["flags"]["vegetation_loss"] == 144
    assert meta["flags"]["vegetation_gain"] == 64


# ── Existing profiles: right class and area on synthetic patches ─────────────


def test_builtup_patch_class_and_area():
    before = _scene(ndvi=0.60, rgb=(60, 110, 60))
    after = _scene(ndvi=0.60, rgb=(60, 110, 60))
    after["indices"]["ndvi"][PATCH] = 0.15
    after["indices"]["ndbi"][PATCH] = 0.40
    after["indices"]["bsi"][PATCH] = 0.30
    after["rgb"][PATCH] = (130, 125, 120)
    mask, _, _, regions = _run_profile("builtup", before, after)

    assert mask[PATCH].all()
    assert regions and regions[0]["change_type"] == "Urban expansion / new construction"
    assert regions[0]["area_ha"] == pytest.approx(1.44)


def test_deforestation_patch_class_and_area():
    before = _scene(ndvi=0.70, nbr=0.60, rgb=(50, 100, 50))
    after = _scene(ndvi=0.70, nbr=0.60, rgb=(50, 100, 50))
    after["indices"]["ndvi"][PATCH] = 0.12
    after["indices"]["nbr"][PATCH] = 0.15
    after["rgb"][PATCH] = (120, 85, 55)
    mask, _, _, regions = _run_profile("deforestation", before, after)

    assert mask[PATCH].all()
    assert regions and regions[0]["change_type"] == "Deforestation / vegetation loss"
    assert regions[0]["area_ha"] == pytest.approx(1.44)


# ── Water relabel ────────────────────────────────────────────────────────────


def test_relabel_water_regions_prioritises_after_state():
    regions = [
        {"change_type": "X", "stats": {"ndvi_before": -0.3, "ndvi_after": -0.4}},
        {"change_type": "X", "stats": {"ndvi_before": -0.3, "ndvi_after": 0.2}},
        {"change_type": "X", "stats": {}},
    ]
    relabel_water_regions(regions)
    assert regions[0]["change_type"] == WATER_GAIN_LABEL
    assert regions[1]["change_type"] == WATER_LOSS_LABEL
    assert regions[2]["change_type"] == "X"   # no index stats: leave untouched


# ── Explanations ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("change_type", sorted(TEMPLATES))
def test_explanations_are_plain_and_claim_free(change_type):
    region = {"change_type": change_type, "stats": {"ndvi_before": 0.72, "ndvi_after": 0.11}}
    text = explain_region(region, "general")
    assert text.strip()
    assert len(text) < 400
    _claim_free(text)


def test_explanation_inserts_measured_numbers_and_falls_back():
    region = {"change_type": "Deforestation / vegetation loss", "stats": {"ndvi_before": 0.72, "ndvi_after": 0.11}}
    text = explain_region(region, "deforestation")
    assert "0.72" in text and "0.11" in text

    unknown = {"change_type": "A label nobody wrote a template for"}
    assert explain_region(unknown, "general").endswith("no rule agreed on a cause.")


# ── Class table ──────────────────────────────────────────────────────────────


def test_class_table_aggregates_sorts_and_totals():
    regions = [
        {"change_type": "A", "area_ha": 0.32, "area_m2": 3200.0},
        {"change_type": "B", "area_ha": 0.09, "area_m2": 900.0},
        {"change_type": "A", "area_ha": 0.05, "area_m2": 500.0},
    ]
    table = build_class_table(regions, aoi_area_ha=100.0)

    assert [row["change_type"] for row in table["rows"]] == ["A", "B"]
    assert table["rows"][0]["area_ha"] == 0.37
    assert table["rows"][0]["region_count"] == 2
    assert table["rows"][0]["percent_of_aoi"] == pytest.approx(0.37)
    assert table["total"]["area_ha"] == pytest.approx(0.46)
    assert table["total"]["region_count"] == 3
    assert "largest 20" in table["note"]


def test_class_table_numbers_match_between_csv_and_geojson():
    regions = [
        {"bounding_box": [0, 0, 10, 10], "change_type": "New surface water", "confidence_label": "High",
         "pixel_area": 100, "area_ha": 1.0, "area_m2": 10000.0, "explanation": "Water-like in the after image."},
        {"bounding_box": [20, 20, 5, 5], "change_type": "Water lost", "confidence_label": "Medium",
         "pixel_area": 25, "area_ha": 0.25, "area_m2": 2500.0},
    ]
    result = {
        "profile": "water",
        "aoi": {"bbox": [10.0, 20.0, 10.01, 20.005]},
        "image_shape": [40, 40],
        "change_regions": regions,
        "class_table": build_class_table(regions, aoi_area_ha=10.0),
    }
    csv_text = regions_to_csv(result)
    geojson = regions_to_geojson(result)

    assert "\nclass_summary\n" in csv_text
    csv_block = csv_text.split("class_summary\n", 1)[1]
    csv_rows = [line.split(",") for line in csv_block.strip().splitlines() if not line.startswith("#")]
    assert csv_rows[0][:2] == ["class", "area_ha"]
    geo_rows = geojson["metadata"]["class_table"]["rows"]
    for csv_row, geo_row in zip(csv_rows[1:-1], geo_rows):
        assert csv_row[0] == geo_row["change_type"]
        assert float(csv_row[1]) == pytest.approx(geo_row["area_ha"])
        assert float(csv_row[3]) == pytest.approx(geo_row["percent_of_aoi"])
        assert int(csv_row[4]) == geo_row["region_count"]
    total = geojson["metadata"]["class_table"]["total"]
    csv_total = csv_rows[-1]
    assert csv_total[0] == "Total"
    assert float(csv_total[1]) == pytest.approx(total["area_ha"])

    assert geojson["features"][0]["properties"]["explanation"].startswith("Water-like")


def test_csv_without_class_table_keeps_old_format():
    result = {
        "change_regions": [
            {"bounding_box": [0, 0, 5, 5], "pixel_area": 25, "change_type": "x", "confidence_label": "Low"}
        ],
    }
    text = regions_to_csv(result)
    lines = text.strip().splitlines()
    assert lines[0].startswith("region_id,change_type")
    assert len(lines) == 2
    assert "class_summary" not in text


# ── Profile warnings ─────────────────────────────────────────────────────────


def test_agriculture_profile_warnings_cover_crop_cycle_and_bare_soil():
    base = profile_warnings("agriculture", [])
    assert [warning["code"] for warning in base] == ["crop_cycle"]
    assert "harvest" in base[0]["message"]

    with_bare_soil = profile_warnings(
        "agriculture", [{"change_type": "Likely bare soil / land clearing"}]
    )
    codes = [warning["code"] for warning in with_bare_soil]
    assert "crop_cycle" in codes and "agriculture_ambiguity" in codes
    ambiguity = next(w for w in with_bare_soil if w["code"] == "agriculture_ambiguity")
    assert ambiguity["severity"] == "warning"
    _claim_free(ambiguity["message"])


def test_other_profiles_add_no_extra_warnings():
    assert profile_warnings("general", []) == []
    assert profile_warnings("water", []) == []
    assert profile_warnings("builtup", []) == []
