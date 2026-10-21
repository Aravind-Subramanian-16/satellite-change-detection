import importlib.util

import numpy as np
import pytest

from benchmarks import finetune_cnn as ft
from learned_features import TestCityLeakError


def test_checkpoint_guard_never_writes_shipped_models(tmp_path):
    for name in ("best_model.pt", "model.onnx"):
        with pytest.raises(ft.CheckpointGuardError):
            ft.assert_safe_checkpoint(tmp_path / name)
    safe = ft.assert_safe_checkpoint(tmp_path / "cnn_finetuned_oscd.pt")
    assert safe.name == "cnn_finetuned_oscd.pt"


def test_crop_coordinates_and_sampling_are_deterministic():
    coordinates = ft.crop_coordinates(600, 600, crop=256, stride=128)
    assert (0, 0) in coordinates
    assert (344, 344) in coordinates
    assert all(0 <= row <= 344 and 0 <= col <= 344 for row, col in coordinates)
    assert ft.crop_coordinates(200, 300) == []

    first = ft.sample_coordinates(600, 600, max_crops=7, seed=3)
    second = ft.sample_coordinates(600, 600, max_crops=7, seed=3)
    assert first == second and len(first) == 7


def test_threshold_selection_uses_validation_pixels():
    probabilities = np.array([0.9, 0.8, 0.7, 0.2, 0.1, 0.05], dtype=np.float32)
    labels = np.array([1, 1, 1, 0, 0, 0], dtype=bool)
    threshold, rows = ft.select_probability_threshold(probabilities, labels)
    assert threshold == pytest.approx(0.5)
    assert max(row["f1"] for row in rows) == pytest.approx(1.0)
    assert ft.scores(probabilities >= threshold, labels)["f1"] == pytest.approx(1.0)


def test_finetune_loader_rejects_test_city_before_reading(tmp_path):
    with pytest.raises(TestCityLeakError):
        ft.load_train_city(tmp_path, tmp_path, "brasilia")


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch is not installed locally")
def test_synthetic_crop_dataset_shapes_when_torch_is_available():
    rng = np.random.default_rng(4)
    city = {
        "a": rng.integers(0, 255, size=(256, 256, 3), dtype=np.uint8),
        "b": rng.integers(0, 255, size=(256, 256, 3), dtype=np.uint8),
        "mask": np.zeros((256, 256), dtype=np.uint8),
    }
    city["mask"][64:128, 64:128] = 1
    dataset = ft._to_tensor({"train_a": city}, [{"city": "train_a", "row": 0, "col": 0}], training=True, seed=1)
    a, b, label = dataset[0]
    assert tuple(a.shape) == (3, 256, 256)
    assert tuple(b.shape) == (3, 256, 256)
    assert tuple(label.shape) == (1, 256, 256)
    assert float(label.max()) == 1.0
