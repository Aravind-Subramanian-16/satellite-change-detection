"""Pseudo-invariant-feature (PIF) radiometric matching between two dates.

A robust affine fit on the least-changing pixels reduces gain/offset differences
between acquisitions before differencing. It is not atmospheric correction and
is not used by the default pipeline.
"""
from __future__ import annotations

import numpy as np


def fit_pif(reference: np.ndarray, target: np.ndarray, pif_percentile: float = 60.0) -> dict:
    """Fit target ≈ gain * reference + offset on pseudo-invariant pixels."""
    reference = np.asarray(reference, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if reference.shape != target.shape:
        raise ValueError("reference and target must have identical shapes")
    finite = np.isfinite(reference) & np.isfinite(target)
    if finite.sum() < 16:
        return {"gain": 1.0, "offset": 0.0, "pif_pixels": int(finite.sum()), "applied": False}
    difference = np.abs(target[finite] - reference[finite])
    limit = float(np.percentile(difference, float(np.clip(pif_percentile, 10.0, 95.0))))
    stable = finite & (np.abs(target - reference) <= limit)
    if stable.sum() < 16:
        return {"gain": 1.0, "offset": 0.0, "pif_pixels": int(stable.sum()), "applied": False}
    x = reference[stable]
    y = target[stable]
    design = np.column_stack([x, np.ones_like(x)])
    gain, offset = np.linalg.lstsq(design, y, rcond=None)[0]
    if not np.isfinite(gain) or abs(float(gain)) < 1e-3:
        return {"gain": 1.0, "offset": 0.0, "pif_pixels": int(stable.sum()), "applied": False}
    return {
        "gain": float(gain),
        "offset": float(offset),
        "pif_pixels": int(stable.sum()),
        "applied": True,
    }


def match_pair(reference: np.ndarray, target: np.ndarray, pif_percentile: float = 60.0) -> np.ndarray:
    """Return target normalised into the reference's radiometric space."""
    target = np.asarray(target, dtype=np.float32)
    fit = fit_pif(reference, target, pif_percentile=pif_percentile)
    if not fit["applied"]:
        return target.copy()
    matched = (target.astype(np.float64) - fit["offset"]) / fit["gain"]
    return np.clip(matched, -1.0, 1.0).astype(np.float32)
