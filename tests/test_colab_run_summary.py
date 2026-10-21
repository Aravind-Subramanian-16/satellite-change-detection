"""Tests for the Colab hand-off summary renderer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.colab_run_summary import render_colab_summary, write_colab_summary  # noqa: E402

COMMIT = "a" * 40
SHA = "b" * 64


def _loco_report() -> dict:
    return {
        "result_status": "computed_on_training_cities_only",
        "guards": {
            "official_test_cities_in_train_list": [],
            "test_labels_path_accepted": False,
        },
        "source": {"train_cities": ["alpha", "bravo"]},
        "protocol": {
            "selection": "Select thresholds on the other training cities.",
            "evaluation": "Apply the selected thresholds to the held-out training city.",
        },
        "families": {
            "hardcoded": {
                "pooled_held_out": {"f1": 0.2, "iou": 0.1, "precision": 0.3, "recall": 0.4},
                "distinct_selected_configs": 2,
                "folds_with_grid_edge_warning": 1,
                "full_train_selection": {
                    "config": {"mode": "hardcoded", "ndvi_drop": -0.3, "ndbi_rise": 0.3},
                    "pooled_f1_on_train_cities_in_sample": 0.25,
                    "grid_edge_warning": "threshold on grid edge",
                },
            },
            "percentile": {
                "pooled_held_out": {"f1": 0.3, "iou": 0.2, "precision": 0.5, "recall": 0.2},
                "distinct_selected_configs": 1,
                "folds_with_grid_edge_warning": 0,
                "full_train_selection": {
                    "config": {"mode": "percentile", "percentile": 99.0},
                    "pooled_f1_on_train_cities_in_sample": 0.35,
                    "grid_edge_warning": None,
                },
            },
        },
        "caveats": ["This is a training-split robustness check, not a test-set result."],
    }


def _model_check() -> dict:
    return {
        "path": "model.onnx",
        "source": "$DRIVE_DIR/weights/model.onnx",
        "size_bytes": 33268410,
        "expected_bytes": 33268410,
        "sha256": SHA,
        "loads": True,
        "input_names": ["input_a", "input_b"],
        "providers": ["CPUExecutionProvider"],
        "error": None,
    }


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    loco = tmp_path / "oscd_loco_thresholds.json"
    loco.write_text(json.dumps(_loco_report()))
    model = tmp_path / "colab_model_check.json"
    model.write_text(json.dumps(_model_check()))
    pytest_summary = tmp_path / "pytest_summary.txt"
    pytest_summary.write_text("128 passed, 3 skipped, 1 warning in 10.27s\n")
    return loco, model, pytest_summary


def test_summary_reads_saved_artifacts_and_marks_scope(tmp_path):
    loco, model, pytest_summary = _write_inputs(tmp_path)
    summary = render_colab_summary(
        loco_path=loco,
        model_check_path=model,
        pytest_summary_path=pytest_summary,
        commit=COMMIT,
        pytest_exit_code=0,
        generated_date="2026-10-21",
    )

    assert f"Code commit: `{COMMIT}`" in summary
    assert "128 passed, 3 skipped" in summary
    assert "| hardcoded | 0.2000 | 0.1000 | 0.3000 | 0.4000 | 2 | 1 |" in summary
    assert "| percentile | 0.3000 | 0.2000 | 0.5000 | 0.2000 | 1 | 0 |" in summary
    assert "Full-train selections (in-sample, not test results)" in summary
    assert "not a test-set score" in summary
    assert "No official OSCD test city was scored" in summary
    assert f"SHA-256: `{SHA}`" in summary
    assert "33,268,410 bytes" in summary
    assert "onnxruntime load: yes" in summary
    assert "`input_a`, `input_b`" in summary
    assert "Generated: 2026-10-21" in summary


def test_write_summary_reports_failed_model_load_without_losing_scope(tmp_path):
    loco, model, pytest_summary = _write_inputs(tmp_path)
    payload = _model_check()
    payload["loads"] = False
    payload["error"] = "protobuf parse failed"
    model.write_text(json.dumps(payload))
    output = tmp_path / "COLAB_RUN_SUMMARY.md"

    summary = write_colab_summary(
        loco_path=loco,
        model_check_path=model,
        pytest_summary_path=pytest_summary,
        commit=COMMIT,
        pytest_exit_code=0,
        output_path=output,
        generated_date="2026-10-21",
    )

    assert output.read_text() == summary
    assert "onnxruntime load: no" in summary
    assert "protobuf parse failed" in summary
    assert "No official OSCD test city was scored" in summary


def test_summary_rewrites_legacy_garbled_test_city_caveat(tmp_path):
    loco, model, pytest_summary = _write_inputs(tmp_path)
    payload = _loco_report()
    payload["caveats"].append(
        "Scores use the same ten official test cities nowhere in this script; "
        "no test label is read."
    )
    loco.write_text(json.dumps(payload))

    summary = render_colab_summary(
        loco_path=loco,
        model_check_path=model,
        pytest_summary_path=pytest_summary,
        commit=COMMIT,
        pytest_exit_code=0,
        generated_date="2026-10-21",
    )

    assert "- No test city is used in this script." in summary
    assert "Scores use the same ten official test cities nowhere" not in summary


def test_summary_rejects_test_city_leakage(tmp_path):
    loco, model, pytest_summary = _write_inputs(tmp_path)
    payload = _loco_report()
    payload["guards"]["official_test_cities_in_train_list"] = ["brasilia"]
    loco.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="official test city"):
        render_colab_summary(
            loco_path=loco,
            model_check_path=model,
            pytest_summary_path=pytest_summary,
            commit=COMMIT,
            pytest_exit_code=0,
        )


def test_summary_rejects_accepted_test_labels_and_bad_hashes(tmp_path):
    loco, model, pytest_summary = _write_inputs(tmp_path)
    payload = _loco_report()
    payload["guards"]["test_labels_path_accepted"] = True
    loco.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="test-label guard"):
        render_colab_summary(
            loco_path=loco,
            model_check_path=model,
            pytest_summary_path=pytest_summary,
            commit=COMMIT,
            pytest_exit_code=0,
        )

    loco.write_text(json.dumps(_loco_report()))
    payload = _model_check()
    payload["sha256"] = "not-a-hash"
    model.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Model SHA-256"):
        render_colab_summary(
            loco_path=loco,
            model_check_path=model,
            pytest_summary_path=pytest_summary,
            commit=COMMIT,
            pytest_exit_code=0,
        )


def test_summary_rejects_empty_pytest_line(tmp_path):
    loco, model, pytest_summary = _write_inputs(tmp_path)
    pytest_summary.write_text("\n")
    with pytest.raises(ValueError, match="Pytest summary is empty"):
        render_colab_summary(
            loco_path=loco,
            model_check_path=model,
            pytest_summary_path=pytest_summary,
            commit=COMMIT,
            pytest_exit_code=0,
        )
