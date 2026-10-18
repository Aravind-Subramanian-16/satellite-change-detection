"""Synthetic tests for OSCD benchmark preprocessing and reporting helpers."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))

from oscd_eval import metrics, preprocess_rgb_pair, run_key, warn_grid_edges, write_table
from spectral_pipeline import SpectralConfig


def test_joint_percentile_uses_shared_acquisition_range_and_uint8():
    before = np.array([[[0, 0, 0], [10, 10, 10]]], dtype=np.float32)
    after = np.array([[[10, 10, 10], [30, 30, 30]]], dtype=np.float32)

    before_scaled, after_scaled = preprocess_rgb_pair(before, after, "joint_percentile")

    assert before_scaled.dtype == after_scaled.dtype == np.uint8
    assert before_scaled.shape == before.shape
    assert after_scaled.shape == after.shape
    # Identical source values map identically across acquisitions under one shared scale.
    repeated_before, repeated_after = preprocess_rgb_pair(before, before, "joint_percentile")
    np.testing.assert_array_equal(repeated_before, repeated_after)
    assert before_scaled[0, 1, 0] == after_scaled[0, 0, 0]
    assert before_scaled[0, 0, 0] < after_scaled[0, 1, 0]
    assert after_scaled.max() == 255


def test_warn_grid_edges_reports_selected_boundary(capsys):
    warn_grid_edges("percentile", SpectralConfig(mode="percentile", percentile=99.5))
    output = capsys.readouterr().out
    assert "WARNING" in output
    assert "percentile=99.5" in output


def test_metrics_include_predicted_and_true_pixel_fractions():
    prediction = np.array([[1, 1], [0, 0]], dtype=bool)
    label = np.array([[1, 0], [0, 0]], dtype=bool)

    result = metrics(prediction, label)

    assert result["predicted_fraction"] == 0.5
    assert result["true_fraction"] == 0.25


def test_markdown_table_reports_fraction_fields(tmp_path):
    prediction = np.array([[1, 1], [0, 0]], dtype=bool)
    label = np.array([[1, 0], [0, 0]], dtype=bool)
    row_metrics = metrics(prediction, label)
    row = {
        "city": "synthetic",
        "pipeline": "cnn",
        "configuration": "cnn_reflectance",
        "selection": "chosen on train",
        "predicted_fraction": row_metrics["predicted_fraction"],
        "true_fraction": row_metrics["true_fraction"],
        "metrics": row_metrics,
    }

    write_table(tmp_path, [row])

    table = (tmp_path / "oscd_results_v2.md").read_text()
    assert "Predicted fraction | True fraction" in table
    assert "| 0.5000 | 0.2500 |" in table


def test_resume_key_includes_preprocess_and_grid_values():
    baseline = run_key("city", "cnn", "cnn", preprocess="reflectance")
    alternate = run_key("city", "cnn", "cnn", preprocess="joint_percentile")
    changed_grid = run_key("city", "spectral", "percentile", grid_values={"percentile": 99.5})

    assert baseline != alternate
    assert changed_grid != run_key("city", "spectral", "percentile", grid_values={"percentile": 99.0})
