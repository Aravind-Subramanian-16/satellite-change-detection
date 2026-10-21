import numpy as np
import pytest

from compositing import clear_fraction, median_composite
from profiles import get_profile
from profiles.detection import detect_profile
from radiometric import fit_pif, match_pair


def test_pif_recovers_affine_gain_and_offset_on_stable_pixels():
    rng = np.random.default_rng(7)
    reference = rng.uniform(0.3, 0.8, size=(40, 40)).astype(np.float32)
    target = reference * 1.25 + 0.03
    target[:20] += 2.0  # half the image is a large unresolved change

    fit = fit_pif(reference, target, pif_percentile=40.0)
    assert fit["applied"] is True
    assert fit["gain"] == pytest.approx(1.25, rel=1e-4)
    assert fit["offset"] == pytest.approx(0.03, abs=1e-5)
    matched = match_pair(reference, target, pif_percentile=40.0)
    assert np.allclose(matched[20:], reference[20:], atol=2e-5)
    assert matched[:20].mean() > matched[20:].mean()


def test_pif_is_a_noop_when_there_are_too_few_pixels():
    fit = fit_pif(np.zeros((3, 3)), np.ones((3, 3)))
    assert fit["applied"] is False
    assert fit["gain"] == 1.0 and fit["offset"] == 0.0
    matched = match_pair(np.zeros((3, 3)), np.ones((3, 3)))
    assert np.array_equal(matched, np.ones((3, 3), dtype=np.float32))


def test_pif_rejects_shape_mismatch_and_clips_matched_values():
    with pytest.raises(ValueError, match="identical shapes"):
        fit_pif(np.zeros((4, 4)), np.zeros((5, 4)))
    rng = np.random.default_rng(11)
    reference = rng.uniform(-0.4, 0.4, size=(30, 30)).astype(np.float32)
    target = reference * 3.0 + 0.8
    matched = match_pair(reference, target)
    assert matched.min() >= -1.0 and matched.max() <= 1.0


def test_median_composite_excludes_masked_pixels_and_returns_nan_when_all_masked():
    arrays = [np.array([[1.0, 2.0], [3.0, 4.0]]), np.array([[5.0, 6.0], [7.0, 8.0]]), np.array([[9.0, 10.0], [11.0, 12.0]])]
    masks = [np.zeros((2, 2), bool), np.ones((2, 2), bool), np.zeros((2, 2), bool)]
    result = median_composite(arrays, masks)
    assert result[0, 0] == pytest.approx(5.0)  # median of 1, 9 with the 5 value masked
    assert result[1, 1] == pytest.approx(8.0)  # median of 4 and 12
    all_masked = median_composite(arrays, [np.ones((2, 2), bool)] * 3)
    assert np.isnan(all_masked).all()


def test_median_composite_validates_inputs():
    with pytest.raises(ValueError, match="at least one"):
        median_composite([])
    with pytest.raises(ValueError, match="match the array shape"):
        median_composite([np.zeros((2, 2))], [np.zeros((3, 3), bool)])


def test_clear_fraction_uses_scl_classes():
    scl = np.array([[4, 4, 3, 8], [9, 10, 5, 5]])
    assert clear_fraction(scl) == pytest.approx(50.0)


def _indices(shape=(40, 40), ndvi=0.6, ndbi=0.0):
    return {key: np.full(shape, value, dtype=np.float32) for key, value in (("ndvi", ndvi), ("ndbi", ndbi), ("nbr", ndvi), ("ndmi", ndvi), ("bsi", ndbi))}


def test_radiometric_normalisation_removes_gain_offset_false_positives():
    before = _indices()
    after = {key: value * 0.8 - 0.10 for key, value in before.items()}
    after["ndvi"][10:20, 10:20] = 0.10
    after["ndbi"][10:20, 10:20] = 0.60

    raw_mask, _, raw_meta = detect_profile(before, after, get_profile("general"), pixel_area_m2=100)
    corrected, _, corrected_meta = detect_profile(
        before, after, get_profile("general"), pixel_area_m2=100, normalise=True
    )

    assert raw_mask[30:40, 30:40].sum() > 0  # gain/offset create stable-area false positives
    assert corrected[30:40, 30:40].sum() == 0
    assert corrected[10:20, 10:20].all()
    assert corrected_meta["radiometric_normalisation"]["ndvi"]["applied"] is True
    assert raw_meta["radiometric_normalisation"] is None
