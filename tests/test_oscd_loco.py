"""Synthetic tests for train-only leave-one-city-out threshold selection."""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.oscd_eval import HARDCODED_NDBI_GRID, HARDCODED_NDVI_GRID, PERCENTILE_GRID  # noqa: E402
from benchmarks.oscd_loco_thresholds import (  # noqa: E402
    assert_training_label_path,
    build_report,
    config_record,
    loco_analysis,
    score_candidates,
    select_entry,
    threshold_candidates,
    validate_train_cities,
)
from spectral_pipeline import SpectralConfig  # noqa: E402


def _synthetic_city(name: str, seed: int, drop_scale: float, rise_scale: float) -> dict:
    """Build index-like training data without rasterio or OSCD files."""
    rng = np.random.default_rng(seed)
    shape = (12, 14)
    ndvi_a = np.full(shape, -0.20, dtype=np.float32)
    ndbi_a = np.full(shape, 0.10, dtype=np.float32)
    drop = rng.random(shape, dtype=np.float32) * drop_scale
    rise = rng.random(shape, dtype=np.float32) * rise_scale
    return {
        "city": name,
        "ndvi_a": ndvi_a,
        "ndbi_a": ndbi_a,
        "ndvi_b": ndvi_a - drop,
        "ndbi_b": ndbi_a + rise,
        "mask": (drop > 0.28) | (rise > 0.18),
    }


def _cities() -> list[dict]:
    return [
        _synthetic_city("alpha", 1, 0.60, 0.40),
        _synthetic_city("bravo", 2, 0.20, 0.10),
        _synthetic_city("charlie", 3, 0.80, 0.60),
        _synthetic_city("delta", 4, 0.05, 0.05),
    ]


def _counts(tp: int, fp: int, fn: int, tn: int) -> dict[str, int]:
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def test_candidates_match_the_benchmark_grids_and_exclude_otsu():
    candidates = threshold_candidates()
    hardcoded = [config for family, config in candidates if family == "hardcoded"]
    percentile = [config for family, config in candidates if family == "percentile"]

    assert len(hardcoded) == len(HARDCODED_NDVI_GRID) * len(HARDCODED_NDBI_GRID) == 30
    assert len(percentile) == len(PERCENTILE_GRID) == 8
    assert {config.percentile for config in percentile} == set(PERCENTILE_GRID)
    assert {config.ndvi_drop for config in hardcoded} == set(HARDCODED_NDVI_GRID)
    assert {config.ndbi_rise for config in hardcoded} == set(HARDCODED_NDBI_GRID)
    assert all(config.use_cloud_mask is False for _, config in candidates)
    assert all(config.mode != "otsu" for _, config in candidates)
    with pytest.raises(ValueError, match="hardcoded and percentile"):
        config_record(SpectralConfig(mode="otsu"))


def test_loco_selects_without_the_held_out_city_and_reports_its_counts():
    cities = _cities()
    scored = score_candidates(cities)
    analysis = loco_analysis(scored, [city["city"] for city in cities])

    assert set(analysis) == {"hardcoded", "percentile"}
    for family, values in analysis.items():
        assert len(values["folds"]) == len(cities)
        assert sum(row["count"] for row in values["selected_config_frequencies"]) == len(cities)
        pooled = {field: sum(fold["held_out_counts"][field] for fold in values["folds"]) for field in ("tp", "fp", "fn", "tn")}
        for field, count in pooled.items():
            assert values["pooled_held_out"][field] == count

        entries = scored[family]
        for fold in values["folds"]:
            selected = next(entry for entry in entries if entry["config"] == fold["selected_config"])
            assert fold["held_out_counts"] == selected["counts"][fold["held_out_city"]]
            assert fold["held_out_metrics"]["tp"] == fold["held_out_counts"]["tp"]
            assert fold["held_out_metrics"]["predicted_fraction"] == pytest.approx(
                (fold["held_out_counts"]["tp"] + fold["held_out_counts"]["fp"])
                / sum(fold["held_out_counts"].values())
            )


def test_held_out_counts_do_not_influence_its_own_selection():
    cities = _cities()
    scored = score_candidates(cities)
    names = [city["city"] for city in cities]
    baseline = loco_analysis(scored, names)
    held_out = names[0]
    perturbed = copy.deepcopy(scored)
    for entries in perturbed.values():
        for entry in entries:
            entry["counts"][held_out] = _counts(0, 0, 10_000, 0)
    changed = loco_analysis(perturbed, names)

    for family in scored:
        before = next(fold for fold in baseline[family]["folds"] if fold["held_out_city"] == held_out)
        after = next(fold for fold in changed[family]["folds"] if fold["held_out_city"] == held_out)
        assert before["selected_config"] == after["selected_config"]
        assert before["selection_f1_on_other_cities"] == after["selection_f1_on_other_cities"]
        assert after["held_out_counts"] == _counts(0, 0, 10_000, 0)


def test_pooled_f1_selection_and_ties_keep_candidate_order():
    cities = ["a", "b", "c"]
    entries = [
        {"config": {"mode": "percentile", "percentile": 99.0}, "counts": {city: _counts(9, 1, 1, 89) for city in cities}},
        {"config": {"mode": "percentile", "percentile": 99.5}, "counts": {city: _counts(9, 1, 1, 89) for city in cities}},
        {"config": {"mode": "percentile", "percentile": 95.0}, "counts": {city: _counts(5, 5, 5, 85) for city in cities}},
        {
            "config": {"mode": "percentile", "percentile": 80.0},
            "counts": {
                "a": _counts(20, 0, 0, 80),
                "b": _counts(0, 10, 10, 80),
                "c": _counts(0, 10, 10, 80),
            },
        },
    ]

    selected = select_entry(entries, cities)
    assert selected["config"]["percentile"] == 99.0
    assert selected["tied_candidates"] == 2
    assert selected["f1_on_selection_cities"] == pytest.approx(0.9)

    without_a = select_entry(entries, ["b", "c"])
    assert without_a["config"]["percentile"] == 99.0
    assert without_a["tied_candidates"] == 2


def test_training_city_and_label_path_guards():
    validate_train_cities(["alpha", "bravo"])
    with pytest.raises(ValueError, match="official test cities"):
        validate_train_cities(["alpha", "brasilia"])
    with pytest.raises(ValueError, match="duplicate"):
        validate_train_cities(["alpha", "alpha"])
    with pytest.raises(ValueError, match="empty"):
        validate_train_cities([])
    with pytest.raises(ValueError, match="test-label"):
        assert_training_label_path(Path("/content/oscd/Test Labels"))
    assert_training_label_path(Path("/content/oscd/Train Labels"))


def test_loco_requires_at_least_three_cities():
    scored = score_candidates(_cities())
    with pytest.raises(ValueError, match="at least three"):
        loco_analysis(scored, ["alpha", "bravo"])


def test_build_report_reads_only_the_train_list_and_assembles_metadata(tmp_path, monkeypatch):
    images = tmp_path / "images"
    images.mkdir()
    names = ["alpha", "bravo", "charlie", "delta"]
    (images / "train.txt").write_text("\n".join(names) + "\n")
    labels = tmp_path / "Train Labels"
    labels.mkdir()
    by_name = {city["city"]: city for city in _cities()}
    monkeypatch.setattr("benchmarks.oscd_loco_thresholds.load_city", lambda _images, _labels, city: by_name[city])

    report = build_report(images, labels, show_progress=False)

    assert report["source"]["train_cities"] == names
    assert report["source"]["train_list_sha256"]
    assert report["guards"]["official_test_cities_in_train_list"] == []
    assert report["guards"]["test_labels_path_accepted"] is False
    assert report["result_status"] == "computed_on_training_cities_only"
    assert report["grids"]["candidate_count"] == 38
    assert set(report["families"]) == {"hardcoded", "percentile"}
    assert all(len(values["folds"]) == len(names) for values in report["families"].values())
    assert "not a test-set result" in report["caveats"][0]

    (images / "train.txt").write_text("alpha\nbrasilia\ncharlie\n")
    with pytest.raises(ValueError, match="official test cities"):
        build_report(images, labels, show_progress=False)
