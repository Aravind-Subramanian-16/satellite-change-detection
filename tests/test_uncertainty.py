import numpy as np
import pytest

from learned_features import TestCityLeakError
from uncertainty import agreement_map, evaluate_ensemble, expected_calibration_error, reliability_bins


def test_ece_is_near_zero_for_calibrated_synthetic_probabilities():
    probabilities, labels = [], []
    for index in range(10):
        confidence = (index + 0.5) / 10.0
        positives = index * 10 + 5
        probabilities.extend([confidence] * 100)
        labels.extend([True] * positives + [False] * (100 - positives))
    result = expected_calibration_error(np.array(probabilities), np.array(labels), n_bins=10)
    assert result["ece"] == pytest.approx(0.0, abs=1e-8)
    assert result["mce"] == pytest.approx(0.0, abs=1e-8)
    assert len(reliability_bins(np.array(probabilities), np.array(labels))) == 10


def test_ece_detects_overconfidence():
    result = expected_calibration_error(np.full(50, 0.9), np.zeros(50, dtype=bool), n_bins=10)
    assert result["ece"] == pytest.approx(0.9)
    assert result["bins"][-1]["count"] == 50


def test_calibration_input_validation():
    with pytest.raises(ValueError, match="same number"):
        expected_calibration_error(np.zeros(4), np.zeros(3, dtype=bool))
    with pytest.raises(ValueError, match="within"):
        expected_calibration_error(np.array([-0.1, 0.5]), np.array([0, 1]))
    with pytest.raises(ValueError, match="non-finite"):
        expected_calibration_error(np.array([np.nan]), np.array([0]))
    with pytest.raises(ValueError, match="positive"):
        reliability_bins(np.array([0.5]), np.array([1]), n_bins=0)


def test_agreement_map_reports_identical_and_opposite_models():
    left = np.zeros((4, 4), dtype=np.float32)
    identical, meta = agreement_map([left, left])
    assert identical.sum() == 0 and meta["mean_disagreement"] == 0
    opposite, meta = agreement_map([left, np.ones((4, 4), dtype=np.float32)])
    assert opposite.min() == 1 and opposite.max() == 1
    assert meta["fraction_disagreeing_over_0_25"] == 100.0


def test_ensemble_evaluation_is_restricted_to_held_out_train_cities():
    maps = [np.full((4, 4), 0.2), np.full((4, 4), 0.8)]
    labels = np.zeros((4, 4), dtype=bool)
    result = evaluate_ensemble(
        maps,
        labels,
        cities=["train_a"],
        held_out_train_cities=["train_a"],
        n_bins=5,
    )
    assert result["calibration"]["ece"] == pytest.approx(0.5)
    assert result["agreement"]["mean_disagreement"] == pytest.approx(0.6)
    with pytest.raises(TestCityLeakError):
        evaluate_ensemble(maps, labels, cities=["brasilia"], held_out_train_cities=["brasilia"])
    with pytest.raises(ValueError, match="held-out TRAIN"):
        evaluate_ensemble(maps, labels, cities=["train_a"], held_out_train_cities=["train_b"])
    with pytest.raises(ValueError, match="at least two"):
        agreement_map([maps[0]])
