import numpy as np
import pytest

from learned_features import (
    BAND_KEYS,
    INDEX_KEYS,
    OFFICIAL_TEST_CITIES,
    TestCityLeakError,
    assert_no_test_cities,
    build_pixel_features,
)


def _constant_bands(shape=(8, 8), values=None):
    values = values or {
        "B02": 1000.0,
        "B03": 1100.0,
        "B04": 1000.0,
        "B08": 3000.0,
        "B11": 2000.0,
        "B12": 1500.0,
    }
    return {key: np.full(shape, values[key], dtype=np.float32) for key in BAND_KEYS}


def test_feature_stack_shape_names_and_index_math():
    before = _constant_bands()
    after = _constant_bands(values={**{key: 1000.0 for key in BAND_KEYS}, "B08": 3000.0, "B11": 2000.0, "B12": 1500.0})
    stack, names = build_pixel_features(before, after)

    expected_count = len(BAND_KEYS) * 2 + len(INDEX_KEYS) * 2 + len(BAND_KEYS) + len(INDEX_KEYS)
    expected_count += (len(BAND_KEYS) + len(INDEX_KEYS)) * 2
    assert stack.shape == (8, 8, expected_count)
    assert len(names) == expected_count == len(set(names))
    assert np.isfinite(stack).all()
    assert names.index("ndvi_before") >= 0
    ndvi = stack[..., names.index("ndvi_before")]
    assert ndvi == pytest.approx(0.5, abs=1e-6)
    ndbi = stack[..., names.index("ndbi_before")]
    assert ndbi == pytest.approx((2000.0 - 3000.0) / 5000.0, abs=1e-6)


def test_local_means_of_index_difference_are_constant_for_constant_inputs():
    before = _constant_bands()
    before["B04"] = np.full((8, 8), 1000.0, dtype=np.float32)
    before["B08"] = np.full((8, 8), 1000.0 * 13.0 / 7.0, dtype=np.float32)  # NDVI 0.30
    after = _constant_bands()
    after["B04"] = np.full((8, 8), 1000.0, dtype=np.float32)
    after["B08"] = np.full((8, 8), 3000.0, dtype=np.float32)  # NDVI 0.50

    stack, names = build_pixel_features(before, after)
    for feature in ("d_ndvi", "d_ndvi_mean3", "d_ndvi_mean7"):
        values = stack[..., names.index(feature)]
        assert values == pytest.approx(0.2, abs=2e-5), feature


def test_local_mean_features_exist_for_both_window_sizes():
    stack, names = build_pixel_features(_constant_bands(), _constant_bands())
    assert sum(name.endswith("_mean3") for name in names) == len(BAND_KEYS) + len(INDEX_KEYS)
    assert sum(name.endswith("_mean7") for name in names) == len(BAND_KEYS) + len(INDEX_KEYS)


def test_feature_builder_is_deterministic():
    before = _constant_bands()
    after = _constant_bands()
    after["B08"] = np.full((8, 8), 2500.0, dtype=np.float32)
    first, first_names = build_pixel_features(before, after)
    second, second_names = build_pixel_features(before, after)
    assert first_names == second_names
    assert np.array_equal(first, second)


def test_missing_band_and_shape_mismatch_are_rejected():
    before = _constant_bands()
    after = _constant_bands()
    del after["B12"]
    with pytest.raises(ValueError, match="missing B12"):
        build_pixel_features(before, after)

    before = _constant_bands()
    after = _constant_bands(shape=(7, 8))
    with pytest.raises(ValueError, match="share one spatial shape"):
        build_pixel_features(before, after)


def test_test_city_guard_rejects_every_official_city():
    assert_no_test_cities(["train_city_a", "train_city_b"])
    for city in OFFICIAL_TEST_CITIES:
        with pytest.raises(TestCityLeakError):
            assert_no_test_cities(["train_city_a", city.upper()])
