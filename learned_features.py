"""Deterministic per-pixel features for the optional learned OSCD classifier.

The spectral/live pipelines do not import this module. Features combine both
acquisitions' reflectance and five spectral indices, their differences, and
3x3/7x7 local means of those differences.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter

BAND_KEYS = ("B02", "B03", "B04", "B08", "B11", "B12")
INDEX_KEYS = ("ndvi", "ndbi", "nbr", "ndmi", "bsi")
LOCAL_SIZES = (3, 7)
OFFICIAL_TEST_CITIES = (
    "brasilia",
    "montpellier",
    "norcia",
    "rio",
    "saclay_w",
    "valencia",
    "dubai",
    "lasvegas",
    "milano",
    "chongqing",
)


class TestCityLeakError(ValueError):
    """Raised when a training/selection list contains an official test city."""

    __test__ = False


def assert_no_test_cities(cities, test_cities=OFFICIAL_TEST_CITIES) -> None:
    normalized = [str(city).strip().lower() for city in cities if str(city).strip()]
    forbidden = {str(city).strip().lower() for city in test_cities}
    overlap = sorted(set(normalized) & forbidden)
    if overlap:
        raise TestCityLeakError(
            "Refusing to train or select on official OSCD test cities: " + ", ".join(overlap)
        )


def _band(bands: dict, key: str) -> np.ndarray:
    if key not in bands:
        raise ValueError(f"Missing band {key}; required bands are {', '.join(BAND_KEYS)}")
    array = np.asarray(bands[key], dtype=np.float32)
    if array.ndim != 2:
        raise ValueError(f"Band {key} must be a 2-D array, got shape {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"Band {key} contains non-finite values")
    return array


def _indices(bands: dict) -> dict[str, np.ndarray]:
    blue = _band(bands, "B02")
    red = _band(bands, "B04")
    nir = _band(bands, "B08")
    swir1 = _band(bands, "B11")
    swir2 = _band(bands, "B12")
    eps = 1e-6
    return {
        "ndvi": (nir - red) / np.maximum(nir + red, eps),
        "ndbi": (swir1 - nir) / np.maximum(swir1 + nir, eps),
        "nbr": (nir - swir2) / np.maximum(nir + swir2, eps),
        "ndmi": (nir - swir1) / np.maximum(nir + swir1, eps),
        "bsi": ((swir1 + red) - (nir + blue)) / np.maximum((swir1 + red) + (nir + blue), eps),
    }


def _shared_scale(*band_sets: dict) -> float:
    maximum = max(float(np.max(arrays[key])) for arrays in band_sets for key in BAND_KEYS)
    return 10000.0 if maximum > 1000.0 else 1.0


def build_pixel_features(
    bands_before: dict,
    bands_after: dict,
    local_sizes: tuple[int, ...] = LOCAL_SIZES,
) -> tuple[np.ndarray, tuple[str, ...]]:
    """Return an HxWxF float32 feature stack and its ordered feature names.

    Reflectance is scaled to [0, 1] when values look like OSCD's 0-10000 units.
    No label, city name or test-set information enters the feature builder.
    """
    missing = [key for key in BAND_KEYS if key not in bands_before or key not in bands_after]
    if missing:
        raise ValueError(f"Both acquisitions must contain all bands; missing {', '.join(missing)}")
    shape = _band(bands_before, BAND_KEYS[0]).shape
    for key in BAND_KEYS:
        before, after = _band(bands_before, key), _band(bands_after, key)
        if before.shape != shape or after.shape != shape:
            raise ValueError("All bands from both dates must share one spatial shape")

    scale = _shared_scale(bands_before, bands_after)
    scaled_before = {key: _band(bands_before, key) / scale for key in BAND_KEYS}
    scaled_after = {key: _band(bands_after, key) / scale for key in BAND_KEYS}
    indices_before = _indices(scaled_before)
    indices_after = _indices(scaled_after)

    features: list[np.ndarray] = []
    names: list[str] = []
    for key in BAND_KEYS:
        features.append(scaled_before[key])
        names.append(f"{key}_before")
    for key in BAND_KEYS:
        features.append(scaled_after[key])
        names.append(f"{key}_after")
    for key in INDEX_KEYS:
        features.append(indices_before[key])
        names.append(f"{key}_before")
    for key in INDEX_KEYS:
        features.append(indices_after[key])
        names.append(f"{key}_after")

    differences: list[tuple[str, np.ndarray]] = []
    for key in BAND_KEYS:
        differences.append((f"d_{key}", scaled_after[key] - scaled_before[key]))
    for key in INDEX_KEYS:
        differences.append((f"d_{key}", indices_after[key] - indices_before[key]))
    for name, difference in differences:
        features.append(difference)
        names.append(name)
    for name, difference in differences:
        for size in local_sizes:
            if size < 1 or size % 2 == 0:
                raise ValueError(f"local_sizes must be positive odd integers, got {size}")
            features.append(uniform_filter(difference, size=size, mode="nearest"))
            names.append(f"{name}_mean{size}")

    stack = np.stack([np.asarray(feature, dtype=np.float32) for feature in features], axis=-1)
    if not np.isfinite(stack).all():
        raise ValueError("Feature construction produced non-finite values; check reflectance inputs")
    return stack, tuple(names)
