"""Late fusion of spectral change evidence and learned change probability.

This is a research/benchmark component, not part of the default app pipeline.
Weights and thresholds must be selected on held-out TRAIN cities only; the
fused output is always reported without test-set metrics in this checkout.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FusionConfig:
    spectral_weight: float = 0.5
    threshold: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.spectral_weight <= 1.0:
            raise ValueError("spectral_weight must be within [0, 1]")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be within [0, 1]")


def robust_normalise(values: np.ndarray, low_percentile: float = 2.0, high_percentile: float = 98.0) -> np.ndarray:
    """Scale non-negative evidence to [0, 1] using finite percentiles."""
    array = np.asarray(values, dtype=np.float32)
    finite = np.isfinite(array)
    if not finite.any():
        return np.zeros_like(array)
    low, high = np.percentile(array[finite], (low_percentile, high_percentile))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return np.zeros_like(array)
    return np.clip((array - low) / (high - low), 0.0, 1.0).astype(np.float32)


def spectral_evidence(
    ndvi_a: np.ndarray,
    ndbi_a: np.ndarray,
    ndvi_b: np.ndarray,
    ndbi_b: np.ndarray,
) -> np.ndarray:
    """Positive vegetation-loss / built-up-gain evidence used by fusion."""
    arrays = [np.asarray(array, dtype=np.float32) for array in (ndvi_a, ndbi_a, ndvi_b, ndbi_b)]
    if len({array.shape for array in arrays}) != 1:
        raise ValueError("spectral evidence arrays must share one shape")
    evidence = np.maximum(
        np.maximum(arrays[0] - arrays[2], 0.0),
        np.maximum(arrays[3] - arrays[1], 0.0),
    )
    return np.nan_to_num(evidence, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def fuse_scores(
    spectral_score: np.ndarray,
    learned_probability: np.ndarray,
    config: FusionConfig = FusionConfig(),
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (fused score, binary mask, metadata); both inputs must be [0, 1]."""
    spectral = np.asarray(spectral_score, dtype=np.float32)
    learned = np.asarray(learned_probability, dtype=np.float32)
    if spectral.shape != learned.shape:
        raise ValueError("spectral and learned arrays must share one shape")
    spectral = np.clip(np.nan_to_num(spectral, nan=0.0), 0.0, 1.0)
    learned = np.clip(np.nan_to_num(learned, nan=0.0), 0.0, 1.0)
    fused = config.spectral_weight * spectral + (1.0 - config.spectral_weight) * learned
    mask = (fused >= config.threshold).astype(np.uint8)
    meta = {
        "method": "weighted_probability_fusion",
        "spectral_weight": float(config.spectral_weight),
        "learned_weight": float(1.0 - config.spectral_weight),
        "threshold": float(config.threshold),
        "predicted_fraction_percent": round(float(mask.mean() * 100.0), 4),
    }
    return fused.astype(np.float32), mask, meta


def select_fusion_config(
    spectral_score: np.ndarray,
    learned_probability: np.ndarray,
    labels: np.ndarray,
    weights=(0.0, 0.25, 0.5, 0.75, 1.0),
    thresholds=tuple(np.round(np.linspace(0.1, 0.9, 17), 2)),
) -> tuple[FusionConfig, list[dict]]:
    """Exhaustive weight/threshold selection for held-out TRAIN data only."""
    labels = np.asarray(labels, dtype=bool)
    if np.asarray(spectral_score).shape != labels.shape or np.asarray(learned_probability).shape != labels.shape:
        raise ValueError("scores and labels must share one shape")
    rows: list[dict] = []
    for weight in weights:
        for threshold in thresholds:
            config = FusionConfig(spectral_weight=float(weight), threshold=float(threshold))
            _, mask, _ = fuse_scores(spectral_score, learned_probability, config)
            tp = int((mask.astype(bool) & labels).sum())
            fp = int((mask.astype(bool) & ~labels).sum())
            fn = int((~mask.astype(bool) & labels).sum())
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            rows.append({"spectral_weight": float(weight), "threshold": float(threshold), "precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn})
    best = max(rows, key=lambda row: (row["f1"], row["precision"], -row["spectral_weight"], row["threshold"]))
    return FusionConfig(spectral_weight=best["spectral_weight"], threshold=best["threshold"]), rows


def fusion_from_indices(
    indices_a: dict,
    indices_b: dict,
    learned_probability: np.ndarray,
    config: FusionConfig = FusionConfig(),
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Fusion helper using raw NDVI/NDBI arrays (no cloud mask applied here)."""
    evidence = spectral_evidence(
        indices_a["ndvi"], indices_a["ndbi"], indices_b["ndvi"], indices_b["ndbi"]
    )
    return fuse_scores(robust_normalise(evidence), learned_probability, config)


__all__ = [
    "FusionConfig",
    "fuse_scores",
    "fusion_from_indices",
    "robust_normalise",
    "select_fusion_config",
    "spectral_evidence",
]
