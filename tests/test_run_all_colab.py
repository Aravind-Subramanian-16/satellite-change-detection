"""Structural checks for the one-click Colab hand-off notebook."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "run_all_colab.ipynb"


def _code() -> str:
    notebook = json.loads(NOTEBOOK.read_text())
    return "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def test_notebook_runs_the_handoff_steps_without_a_test_scoring_command():
    code = _code()
    for marker in (
        "[setup 1/4]",
        "[a/4] Running the test suite",
        "[b/4] Running train-only leave-one-city-out",
        "[c/4] Checking the Drive model",
        "[d/4] Writing benchmarks/results/COLAB_RUN_SUMMARY.md",
    ):
        assert marker in code
    assert "oscd_loco_thresholds.py" in code
    assert "oscd_eval.py" not in code
    assert "train_pixel_classifier.py" not in code
    assert "finetune" not in code.lower()
    assert "test_labels.zip" not in code
    assert "GITHUB_TOKEN" in code
    assert "Push skipped: copy the block above" in code


def test_notebook_has_no_stored_outputs_or_execution_counts():
    notebook = json.loads(NOTEBOOK.read_text())
    assert notebook["nbformat"] == 4
    assert notebook["cells"]
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        assert cell["outputs"] == []
        assert cell["execution_count"] is None


def test_notebook_warns_that_results_do_not_exist_before_the_run():
    notebook = json.loads(NOTEBOOK.read_text())
    markdown = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )
    assert "No result exists until this notebook is run." in markdown
    assert "does not exist until this run" in markdown
    assert "never unzips, reads or scores the official test labels" in markdown
