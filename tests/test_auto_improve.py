import json

import numpy as np
import pytest

from benchmarks import auto_improve as ai
from learned_features import TestCityLeakError


def _synthetic_city(city: str, offset: int = 0) -> dict:
    shape = (24, 24)
    ndvi_a = np.full(shape, 0.6, dtype=np.float32)
    ndbi_a = np.zeros(shape, dtype=np.float32)
    ndvi_b = ndvi_a.copy()
    ndbi_b = ndbi_a.copy()
    patch = (slice(4 + offset, 12 + offset), slice(4, 12))
    ndvi_b[patch] = 0.2
    ndbi_b[patch] = 0.5
    mask = np.zeros(shape, dtype=bool)
    mask[patch] = True
    return {"city": city, "mask": mask, "ndvi_a": ndvi_a, "ndbi_a": ndbi_a, "ndvi_b": ndvi_b, "ndbi_b": ndbi_b}


def test_leave_city_out_folds_and_guard():
    folds = ai.leave_city_out_folds(["a", "b", "c"])
    assert len(folds) == 3
    assert folds[0]["validation"] == ["a"]
    assert folds[0]["fit"] == ["b", "c"]
    with pytest.raises(TestCityLeakError):
        ai.leave_city_out_folds(["brasilia", "train_a"])


def test_run_search_logs_every_trial_and_validation_only(tmp_path):
    cities = ["train_a", "train_b", "train_c"]
    output = tmp_path / "auto_improve_log.json"
    payload = ai.run_search(
        cities,
        _synthetic_city,
        output,
        systems=ai.SYSTEMS,
        max_trials=ai.HARD_TRIAL_BUDGET,
    )
    assert output.is_file()
    assert output.with_suffix(".md").is_file()
    saved = json.loads(output.read_text())
    assert saved["metadata"]["test_split_read"] is False
    assert saved["metadata"]["official_test_cities_excluded"] == list(ai.OFFICIAL_TEST_CITIES)
    assert saved["metadata"]["trials_attempted"] == len(ai.SYSTEMS) == 12
    assert len(saved["trials"]) == 12
    assert all(trial["status"] == "ok" for trial in saved["trials"])
    assert all(len(trial["folds"]) == 3 for trial in saved["trials"])
    assert saved["metadata"]["complete"] is True
    assert saved["selection"]["status"] == "ok"
    assert len(saved["ablations"]) == 3
    assert all(row["pairs_available"] == 4 for row in saved["ablations"])
    assert "test-set" in (tmp_path / "auto_improve_log.md").read_text().lower()


def test_budget_is_hard_and_failures_are_logged(tmp_path):
    with pytest.raises(ai.BudgetExceeded):
        ai.run_search(["a", "b"], _synthetic_city, tmp_path / "x.json", max_trials=99)
    with pytest.raises(ai.BudgetExceeded):
        ai.run_search(["a", "b"], _synthetic_city, tmp_path / "x.json", systems=ai.SYSTEMS, max_trials=1)

    def failing_loader(city):
        raise ValueError("synthetic loader failure")

    output = tmp_path / "failed.json"
    payload = ai.run_search(["a", "b"], failing_loader, output, systems=(ai.SYSTEMS[0],), max_trials=1)
    saved = json.loads(output.read_text())
    assert saved["trials"][0]["status"] == "failed"
    assert "synthetic loader failure" in saved["trials"][0]["error"]
    assert payload["selection"]["status"] == "no_successful_trials"
    assert saved["metadata"]["complete"] is True


def test_official_test_city_is_rejected_before_any_trial(tmp_path):
    with pytest.raises(TestCityLeakError):
        ai.run_search(["brasilia", "train_a"], _synthetic_city, tmp_path / "x.json")
