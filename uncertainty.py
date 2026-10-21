"""Model-agreement uncertainty and calibration (ECE) for held-out TRAIN cities.

The default app does not use these functions. They exist for the preregistered
Phase D2 analysis and must be evaluated on held-out training cities only.
"""
from __future__ import annotations

import numpy as np

from learned_features import assert_no_test_cities


def _validated(probabilities: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    probabilities = np.asarray(probabilities, dtype=np.float64).ravel()
    labels = np.asarray(labels, dtype=bool).ravel()
    if probabilities.shape != labels.shape:
        raise ValueError("probabilities and labels must have the same number of pixels")
    finite = np.isfinite(probabilities)
    if not finite.all():
        raise ValueError("probabilities contain non-finite values")
    if ((probabilities < 0.0) | (probabilities > 1.0)).any():
        raise ValueError("probabilities must be within [0, 1]")
    return probabilities, labels


def reliability_bins(
    probabilities: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> list[dict]:
    """Equal-width confidence bins with empirical accuracy and ECE contribution."""
    probabilities, labels = _validated(probabilities, labels)
    n_bins = int(n_bins)
    if n_bins < 1:
        raise ValueError("n_bins must be positive")
    bin_ids = np.minimum((probabilities * n_bins).astype(int), n_bins - 1)
    rows = []
    total = probabilities.size
    for index in range(n_bins):
        selected = bin_ids == index
        count = int(selected.sum())
        if count == 0:
            rows.append({"lower": index / n_bins, "upper": (index + 1) / n_bins, "count": 0, "mean_confidence": None, "accuracy": None, "gap": None})
            continue
        confidence = float(probabilities[selected].mean())
        accuracy = float(labels[selected].mean())
        rows.append(
            {
                "lower": index / n_bins,
                "upper": (index + 1) / n_bins,
                "count": count,
                "mean_confidence": confidence,
                "accuracy": accuracy,
                "gap": abs(confidence - accuracy),
                "weight": count / total if total else 0.0,
            }
        )
    return rows


def expected_calibration_error(
    probabilities: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> dict:
    """Return ECE, maximum calibration error and the reliability table."""
    probabilities, labels = _validated(probabilities, labels)
    rows = reliability_bins(probabilities, labels, n_bins=n_bins)
    total = probabilities.size
    ece = sum(row["weight"] * row["gap"] for row in rows if row["count"])
    mce = max((row["gap"] for row in rows if row["count"]), default=0.0)
    return {"ece": float(ece), "mce": float(mce), "n_pixels": int(total), "n_bins": int(n_bins), "bins": rows}


def agreement_map(probability_maps: list[np.ndarray]) -> tuple[np.ndarray, dict]:
    """Mean pairwise disagreement between model probability maps."""
    if len(probability_maps) < 2:
        raise ValueError("agreement requires at least two model probability maps")
    arrays = [np.asarray(array, dtype=np.float32) for array in probability_maps]
    if len({array.shape for array in arrays}) != 1:
        raise ValueError("all probability maps must share one shape")
    stack = np.stack(arrays, axis=0).astype(np.float64)
    if not np.isfinite(stack).all():
        raise ValueError("probability maps contain non-finite values")
    if ((stack < 0.0) | (stack > 1.0)).any():
        raise ValueError("probability maps must be within [0, 1]")
    differences = []
    for left in range(stack.shape[0]):
        for right in range(left + 1, stack.shape[0]):
            differences.append(np.abs(stack[left] - stack[right]))
    disagreement = np.mean(differences, axis=0).astype(np.float32)
    return disagreement, {
        "models": len(arrays),
        "mean_disagreement": float(disagreement.mean()),
        "fraction_disagreeing_over_0_25": float((disagreement > 0.25).mean() * 100.0),
    }


def evaluate_ensemble(
    probability_maps: list[np.ndarray],
    labels: np.ndarray,
    *,
    cities: list[str],
    held_out_train_cities: list[str],
    n_bins: int = 10,
) -> dict:
    """ECE and agreement for ensemble probabilities on held-out TRAIN cities.

    ``cities`` names the cities represented by the pixel arrays. The guard makes
    it impossible to compute these numbers on an official test city by mistake.
    """
    assert_no_test_cities(cities)
    held_out = {str(city).strip().lower() for city in held_out_train_cities}
    used = {str(city).strip().lower() for city in cities}
    if not used <= held_out:
        raise ValueError("Uncertainty/ECE must be evaluated on held-out TRAIN cities only")
    if not probability_maps:
        raise ValueError("probability_maps must contain at least one model")
    labels = np.asarray(labels, dtype=bool)
    if any(np.asarray(array).shape != labels.shape for array in probability_maps):
        raise ValueError("probability maps must match the label shape")
    disagreement, agreement_meta = agreement_map(probability_maps)
    ensemble = np.mean([np.asarray(array, dtype=np.float64) for array in probability_maps], axis=0)
    calibration = expected_calibration_error(ensemble, labels, n_bins=n_bins)
    return {
        "cities": list(cities),
        "held_out_train_cities": list(held_out_train_cities),
        "agreement": agreement_meta,
        "calibration": calibration,
        "mean_probability": float(ensemble.mean()),
        "note": "Validation-only uncertainty; do not report as a test-set calibration result.",
    }


__all__ = [
    "agreement_map",
    "evaluate_ensemble",
    "expected_calibration_error",
    "reliability_bins",
]
