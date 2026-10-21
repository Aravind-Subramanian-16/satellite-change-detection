import numpy as np
import pytest

from postprocess import apply_mmu, morphological_cleanup
from profiles import get_profile, profile_public
from profiles.detection import detect_profile, indices_from_bands, indices_from_encoded


def _indices(value=0.5, shape=(20, 20)):
    return {key: np.full(shape, value, dtype=np.float32) for key in ("ndvi", "ndbi", "nbr", "ndmi", "bsi")}


def test_registry_never_hides_unvalidated_status():
    agriculture = profile_public("agriculture")
    builtup = profile_public("builtup")
    assert agriculture["validation_status"] == "unvalidated, qualitative only"
    assert agriculture["display_metrics"] is False
    assert builtup["validation_status"].startswith("quantitatively benchmarked on OSCD")
    assert "0.12" in builtup["validation_status"]
    with pytest.raises(ValueError):
        get_profile("does-not-exist")


def test_agriculture_flags_stress_and_vegetation_loss():
    before, after = _indices(0.6), _indices(0.6)
    after["ndvi"][5:15, 5:15] = 0.30          # vegetation loss
    after["ndmi"][0:5, 0:20] = 0.30           # moisture stress, smaller NDVI drop
    after["ndvi"][0:5, 0:20] = 0.50
    mask, invalid, meta = detect_profile(before, after, get_profile("agriculture"), pixel_area_m2=100)
    assert not invalid.any()
    assert mask[5:15, 5:15].all()
    assert mask[0:5, 0:20].all()
    assert meta["flags"]["cropland_stress"] > 0
    assert meta["flags"]["vegetation_loss"] > 0


def test_mmu_removes_speckle_but_keeps_large_objects():
    mask = np.zeros((20, 20), np.uint8)
    mask[2:12, 2:12] = 1     # 100 px = 1 ha at 100 m2/px
    mask[18, 18] = 1          # 1 px speckle
    filtered, info = apply_mmu(mask, pixel_area_m2=100, mmu_ha=0.5)
    assert filtered[18, 18] == 0
    assert filtered[2:12, 2:12].all()
    assert info["removed_components"] == 1
    assert info["min_pixels"] == 50


def test_deforestation_requires_vegetated_before_and_mmu():
    before, after = _indices(0.0), _indices(0.0)
    before["ndvi"][:] = 0.7
    before["nbr"][:] = 0.6
    after["ndvi"][:] = 0.2
    after["nbr"][:] = 0.3
    before["ndvi"][0:5, 0:5] = 0.05   # barren before -> must be excluded
    mask, _, meta = detect_profile(before, after, get_profile("deforestation"), pixel_area_m2=100)
    assert not mask[0:5, 0:5].any()
    assert mask[10, 10] == 1
    assert meta["mmu"]["mmu_ha"] == 0.5
    assert meta["cloud_mask_enabled"] is False


def test_deforestation_mmu_removes_small_patch():
    before, after = _indices(0.0), _indices(0.0)
    before["ndvi"][:] = 0.7
    before["nbr"][:] = 0.6
    after["ndvi"][:] = 0.2
    after["nbr"][:] = 0.3
    before["ndvi"][0:20, 0:20] = 0.7
    after["ndvi"][0:20, 0:20] = 0.2
    small = after.copy()
    small["ndvi"][:] = 0.7
    small["nbr"][:] = 0.6
    small["ndvi"][0:3, 0:3] = 0.1
    small["nbr"][0:3, 0:3] = 0.1
    mask, _, _ = detect_profile(before, small, get_profile("deforestation"), pixel_area_m2=100)
    assert mask.sum() == 0


def test_builtup_ndbi_and_bare_soil_cues():
    before, after = _indices(0.0), _indices(0.0)
    before["ndvi"][:] = 0.6
    after["ndvi"][:] = 0.4
    after["ndbi"][5:15, 5:15] = 0.4
    after["bsi"][0:5, 0:5] = 0.3
    after["ndvi"][0:5, 0:5] = 0.2
    mask, _, meta = detect_profile(before, after, get_profile("builtup"), pixel_area_m2=100)
    assert mask[10, 10] == 1
    assert mask[2, 2] == 1
    assert meta["flags"]["ndbi_cue"] > 0
    assert meta["flags"]["bare_soil_cue"] > 0


def test_cloud_shadow_is_masked_mandatorily():
    before, after = _indices(0.0), _indices(0.0)
    before["ndvi"][:] = 0.7
    before["nbr"][:] = 0.6
    after["ndvi"][:] = 0.2
    after["nbr"][:] = 0.3
    scl = np.zeros((20, 20), np.uint8)
    scl[0:5, 0:5] = 3   # cloud shadow
    scl[15:20, 15:20] = 9  # cloud
    mask, invalid, meta = detect_profile(
        before, after, get_profile("deforestation"), scl_a=scl, scl_b=scl, pixel_area_m2=100
    )
    assert invalid[0:5, 0:5].all()
    assert mask[0:5, 0:5].sum() == 0
    assert mask[15:20, 15:20].sum() == 0
    assert meta["masked_percent"] > 0


def test_roads_profile_is_context_only():
    before, after = _indices(0.5), _indices(0.5)
    before["ndvi"][5:15, 5:15] = 0.7
    after["ndvi"][5:15, 5:15] = 0.2
    after["ndbi"][5:15, 5:15] = 0.5
    mask, _, meta = detect_profile(before, after, get_profile("roads"), pixel_area_m2=100)
    assert meta["road_context_only"] is True
    assert "road_context" not in meta  # filled by the live pipeline when OSM is enabled
    assert mask.any()


def test_index_math_from_bands_matches_definitions():
    before = {band: np.full((2, 2), 1000.0) for band in ("B02", "B04", "B08", "B11", "B12")}
    before["B08"] = np.full((2, 2), 4000.0)
    after = {key: value.copy() for key, value in before.items()}
    indices_a, indices_b = indices_from_bands(before, after)
    expected_ndvi = (4000 - 1000) / 5000
    assert indices_a["ndvi"] == pytest.approx(expected_ndvi)
    assert indices_a["ndmi"] == pytest.approx((4000 - 1000) / 5000)
    assert indices_a["nbr"] == pytest.approx((4000 - 1000) / 5000)


def test_encoded_roundtrip_for_extended_indices():
    shape = (2, 2)
    indices = np.dstack([np.full(shape, 191.25), np.full(shape, 127.5), np.full(shape, 0.0)]).astype(np.float32)
    ext = np.dstack([np.full(shape, 191.25), np.full(shape, 191.25), np.full(shape, 127.5)]).astype(np.float32)
    decoded, scl = indices_from_encoded(indices, ext)
    assert decoded["ndvi"] == pytest.approx(0.5, abs=1e-6)
    assert decoded["nbr"] == pytest.approx(0.5, abs=1e-6)
    assert decoded["bsi"] == pytest.approx(0.0, abs=1e-6)
    assert scl.shape == shape


def test_morphological_cleanup_is_a_noop_when_disabled():
    mask = np.zeros((10, 10), np.uint8)
    mask[4:6, 4:6] = 1
    assert np.array_equal(morphological_cleanup(mask), mask)
