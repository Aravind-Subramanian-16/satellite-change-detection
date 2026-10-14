"""Shared Sentinel-2 spectral change detector used by the API and OSCD benchmark."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np

ThresholdMode = Literal["hardcoded", "otsu", "percentile"]
CLOUD_CLASSES = (3, 8, 9, 10)


@dataclass(frozen=True)
class SpectralConfig:
    mode: ThresholdMode = "hardcoded"
    ndvi_drop: float = -0.15
    ndbi_rise: float = 0.10
    percentile: float = 95.0
    mask_cloud_shadow: bool = True
    use_cloud_mask: bool = True


def decode_indices(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decode the app Evalscript's PNG channels into NDVI, NDBI and integer SCL."""
    data = np.asarray(indices, dtype=np.float32)
    if data.ndim != 3 or data.shape[-1] < 2:
        raise ValueError("indices must be an HxWx2+ encoded-index image")
    ndvi = (data[..., 0] / 255.0 - 0.5) * 2.0
    ndbi = (data[..., 1] / 255.0 - 0.5) * 2.0
    scl = np.rint(data[..., 2] / 255.0 * 255.0).astype(np.uint8) if data.shape[-1] >= 3 else np.zeros(ndvi.shape, dtype=np.uint8)
    # CDSE Evalscript emits SCL/255, which arrives losslessly as SCL in AUTO PNG.
    return ndvi, ndbi, scl


def encode_indices(ndvi: np.ndarray, ndbi: np.ndarray, scl: np.ndarray | None = None) -> np.ndarray:
    """Encode arrays exactly like the Evalscript; useful for offline datasets/tests."""
    scl = np.zeros_like(ndvi, dtype=np.uint8) if scl is None else np.asarray(scl, dtype=np.uint8)
    return np.dstack(((np.clip(ndvi, -1, 1) / 2 + 0.5) * 255, (np.clip(ndbi, -1, 1) / 2 + 0.5) * 255, scl)).astype(np.uint8)


def cloud_mask(scl_a: np.ndarray | None, scl_b: np.ndarray | None, include_shadow: bool = True) -> np.ndarray:
    """Return pixels invalid in either acquisition; absent SCL intentionally means no mask."""
    if scl_a is None or scl_b is None:
        shape = scl_a.shape if scl_a is not None else scl_b.shape if scl_b is not None else (0, 0)
        return np.zeros(shape, dtype=bool)
    classes = CLOUD_CLASSES if include_shadow else (8, 9, 10)
    return np.isin(scl_a, classes) | np.isin(scl_b, classes)


def _otsu(values: np.ndarray, fallback: float) -> float:
    values = values[np.isfinite(values)]
    if values.size < 2 or np.ptp(values) < 1e-7:
        return fallback
    hist, edges = np.histogram(values, bins=256)
    centers = (edges[:-1] + edges[1:]) / 2
    weight1 = np.cumsum(hist)
    weight2 = values.size - weight1
    mean1 = np.cumsum(hist * centers) / np.maximum(weight1, 1)
    mean2 = (np.cumsum((hist * centers)[::-1])[::-1] - hist * centers) / np.maximum(weight2, 1)
    between = weight1[:-1] * weight2[:-1] * (mean1[:-1] - mean2[:-1]) ** 2
    return float(centers[int(np.argmax(between))]) if between.size else fallback


def detect_from_indices(
    ndvi_a: np.ndarray, ndbi_a: np.ndarray, ndvi_b: np.ndarray, ndbi_b: np.ndarray,
    scl_a: np.ndarray | None = None, scl_b: np.ndarray | None = None, config: SpectralConfig = SpectralConfig(),
) -> tuple[np.ndarray, np.ndarray, dict[str, float | str | bool]]:
    """Return (change mask, invalid cloud mask, reproducible threshold metadata)."""
    dvi, dbi = np.asarray(ndvi_b) - np.asarray(ndvi_a), np.asarray(ndbi_b) - np.asarray(ndbi_a)
    invalid = cloud_mask(scl_a, scl_b, config.mask_cloud_shadow) if config.use_cloud_mask else np.zeros(dvi.shape, dtype=bool)
    valid = ~invalid & np.isfinite(dvi) & np.isfinite(dbi)
    if config.mode == "hardcoded":
        vi_threshold, bi_threshold = config.ndvi_drop, config.ndbi_rise
    elif config.mode == "otsu":
        # Otsu operates on positive change evidence so the directions remain semantic.
        vi_threshold = -_otsu((-dvi)[valid], abs(config.ndvi_drop))
        bi_threshold = _otsu(dbi[valid], config.ndbi_rise)
    elif config.mode == "percentile":
        vi_threshold = -float(np.percentile((-dvi)[valid], config.percentile)) if valid.any() else config.ndvi_drop
        bi_threshold = float(np.percentile(dbi[valid], config.percentile)) if valid.any() else config.ndbi_rise
    else:
        raise ValueError(f"Unknown threshold mode: {config.mode}")
    mask = ((dvi < vi_threshold) | (dbi > bi_threshold)) & valid
    return mask.astype(np.uint8), invalid, {"mode": config.mode, "ndvi_drop_threshold": float(vi_threshold), "ndbi_rise_threshold": float(bi_threshold), "cloud_mask_enabled": config.use_cloud_mask, "masked_percent": float(invalid.mean() * 100)}
