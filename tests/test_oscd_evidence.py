"""Tests for saved-result baselines, bootstrap and failure summaries."""
import hashlib
import json
import sys
from pathlib import Path

import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.oscd_eval import OFFICIAL_TEST_CITIES  # noqa: E402
from benchmarks.oscd_evidence import (  # noqa: E402
    build_evidence,
    compute_metrics,
    load_results,
    pooled,
    render_markdown,
)

RESULTS = ROOT / "benchmarks/results/oscd_results_v2.json"
METHOD_ROWS = {
    "hardcoded": ("spectral", "hardcoded", None, 10, 5, 20, 965),
    "percentile": ("spectral", "percentile", None, 15, 10, 15, 960),
    "otsu": ("spectral", "otsu", None, 30, 500, 0, 470),
    "cnn_joint": ("cnn", "pipeline_a_cnn_joint_percentile_chosen_on_train", "joint_percentile", 0, 0, 30, 970),
    "cnn_reflectance": ("cnn", "pipeline_a_cnn_reflectance_other", "reflectance", 0, 0, 30, 970),
}


def _row(city: str, method: str, counts: tuple[int, int, int, int] | None = None) -> dict:
    pipeline, configuration, preprocess, *default = METHOD_ROWS[method]
    tp, fp, fn, tn = counts or tuple(default)
    values = compute_metrics(tp, fp, fn, tn)
    row = {
        "city": city,
        "pipeline": pipeline,
        "configuration": configuration,
        "split": "test",
        "metrics": values,
        "predicted_fraction": values["predicted_fraction"],
        "true_fraction": values["true_fraction"],
    }
    if preprocess:
        row["preprocess"] = preprocess
        row["selection"] = "chosen on train" if method == "cnn_joint" else "other"
    return row


def _fake_rows() -> list[dict]:
    return [_row(city, method) for city in OFFICIAL_TEST_CITIES for method in METHOD_ROWS]


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "results.json"
    path.write_text(json.dumps(rows))
    return path


def test_validation_rejects_missing_duplicate_nontest_and_inconsistent_rows(tmp_path):
    rows = _fake_rows()
    missing = [row for row in rows if not (row["city"] == "brasilia" and row["pipeline"] == "cnn")]
    with pytest.raises(ValueError, match="Missing cnn"):
        load_results(_write(tmp_path, missing), expected_cities=OFFICIAL_TEST_CITIES)

    with pytest.raises(ValueError, match="Duplicate"):
        load_results(_write(tmp_path, rows + [rows[0]]), expected_cities=OFFICIAL_TEST_CITIES)

    non_test = [dict(row) for row in rows]
    non_test[0]["split"] = "train"
    with pytest.raises(ValueError, match="test results only"):
        load_results(_write(tmp_path, non_test), expected_cities=OFFICIAL_TEST_CITIES)

    inconsistent = [dict(row) for row in rows]
    inconsistent[0] = {**inconsistent[0], "metrics": {**inconsistent[0]["metrics"], "f1": 0.123}}
    with pytest.raises(ValueError, match="f1 does not match"):
        load_results(_write(tmp_path, inconsistent), expected_cities=OFFICIAL_TEST_CITIES)

    with pytest.raises(ValueError, match="official test cities"):
        load_results(_write(tmp_path, rows), expected_cities=("alpha", "bravo"))


def test_baselines_use_prevalence_expectation():
    metrics = compute_metrics(10, 10, 30, 950)
    from benchmarks.oscd_evidence import baseline_summary

    baselines = baseline_summary(metrics)
    prevalence = 40 / 1000
    assert baselines["all_no_change"]["f1"] == 0.0
    assert baselines["all_no_change"]["recall"] == 0.0
    assert baselines["random_at_prevalence"]["f1"] == pytest.approx(prevalence)
    assert baselines["random_at_prevalence"]["precision"] == pytest.approx(prevalence)
    assert baselines["random_at_prevalence"]["recall"] == pytest.approx(prevalence)
    assert baselines["random_at_prevalence"]["iou"] == pytest.approx(prevalence / (2 - prevalence))


def test_bootstrap_is_deterministic_and_pairs_each_method_with_hardcoded(tmp_path):
    from benchmarks.oscd_evidence import bootstrap_summary

    by_method = load_results(_write(tmp_path, _fake_rows()), expected_cities=OFFICIAL_TEST_CITIES)
    first = bootstrap_summary(by_method, seed=0, resamples=300)
    second = bootstrap_summary(by_method, seed=0, resamples=300)
    assert first == second
    assert first["seed"] == 0
    assert first["resamples"] == 300
    assert first["n_cities"] == 10
    assert "paired_vs_hardcoded" not in first["methods"]["hardcoded"]
    for name in ("percentile", "otsu", "cnn_joint", "cnn_reflectance"):
        paired = first["methods"][name]["paired_vs_hardcoded"]["f1"]
        assert paired["point"] == pytest.approx(pooled(by_method[name])["f1"] - pooled(by_method["hardcoded"])["f1"])
        assert 0.0 <= paired["fraction_resamples_positive"] <= 1.0
        low, high = paired["ci95"]
        assert low <= high
        for method in (name, "hardcoded"):
            low, high = first["methods"][method]["f1"]["ci95"]
            assert low <= high


def test_failure_summary_flags_empty_cnn_and_overpredicting_otsu(tmp_path):
    from benchmarks.oscd_evidence import failure_summary, per_city_summary

    by_method = load_results(_write(tmp_path, _fake_rows()), expected_cities=OFFICIAL_TEST_CITIES)
    per_city = per_city_summary(by_method)
    failure = failure_summary(by_method, per_city)

    assert set(failure["cnn_zero_prediction_cities"]["cnn_joint"]) == set(OFFICIAL_TEST_CITIES)
    assert set(failure["cnn_zero_prediction_cities"]["cnn_reflectance"]) == set(OFFICIAL_TEST_CITIES)
    assert failure["otsu"]["over_predicted_cities"] == sorted(OFFICIAL_TEST_CITIES)
    assert failure["prediction_balance"]["hardcoded"]["under"] == sorted(OFFICIAL_TEST_CITIES)
    assert failure["correlations"]["cnn_reflectance"]["true_fraction_vs_f1_pearson"] is None


def test_evidence_builds_from_a_file_without_reading_imagery(tmp_path):
    rows = _fake_rows()
    source = _write(tmp_path, rows)
    before = source.read_bytes()
    evidence = build_evidence(source, resamples=100, expected_cities=OFFICIAL_TEST_CITIES)

    assert source.read_bytes() == before
    assert evidence["source"]["sha256"] == hashlib.sha256(before).hexdigest()
    assert evidence["scope"].startswith("saved per-city test confusion counts only")
    assert evidence["cities"] == sorted(OFFICIAL_TEST_CITIES)
    assert evidence["bootstrap"]["resamples"] == 100
    markdown = render_markdown(evidence)
    for text in ("City-level bootstrap", "Failure analysis", "Pipeline specification", "Caveats", "No causal"):
        assert text in markdown
    assert "All-no-change F1" in markdown


@pytest.mark.skipif(not RESULTS.is_file(), reason="saved v2 results are not present")
def test_saved_v2_results_match_published_evidence_values():
    assert hashlib.sha256(RESULTS.read_bytes()).hexdigest() == "37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f"
    by_method = load_results(RESULTS, expected_cities=OFFICIAL_TEST_CITIES)
    assert {name: len(rows) for name, rows in by_method.items()} == {name: 10 for name in METHOD_ROWS}

    hardcoded = pooled(by_method["hardcoded"])
    percentile = pooled(by_method["percentile"])
    otsu = pooled(by_method["otsu"])
    cnn_joint = pooled(by_method["cnn_joint"])
    cnn_reflectance = pooled(by_method["cnn_reflectance"])
    assert hardcoded["f1"] == pytest.approx(0.0782, abs=1e-4)
    assert percentile["f1"] == pytest.approx(0.1176, abs=1e-4)
    assert otsu["f1"] == pytest.approx(0.0953, abs=1e-4)
    assert otsu["predicted_fraction"] == pytest.approx(0.6735, abs=1e-4)
    assert cnn_joint["f1"] == pytest.approx(0.0007, abs=1e-4)
    assert cnn_reflectance["f1"] == 0.0
    assert hardcoded["true_fraction"] == pytest.approx(0.0517, abs=1e-4)
