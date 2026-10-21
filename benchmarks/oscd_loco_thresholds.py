#!/usr/bin/env python3
"""Leave-one-training-city-out robustness check for spectral thresholds.

Only training cities and training labels are read. The script accepts no
test-label path and refuses to run when an official OSCD test city appears in
``train.txt``. Threshold candidates are the same grids used by
``benchmarks/oscd_eval.py``.

This is a robustness check on the training split, not a test-set result. It
does not replace the saved test scores in ``oscd_results_v2.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from datetime import date
from pathlib import Path

from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.oscd_eval import (  # noqa: E402
    HARDCODED_NDBI_GRID,
    HARDCODED_NDVI_GRID,
    OFFICIAL_TEST_CITIES,
    PERCENTILE_GRID,
    grid_edge_warning,
    load_city,
    metrics,
    read_city_list,
    spectral_prediction,
)
from spectral_pipeline import SpectralConfig  # noqa: E402

COUNT_FIELDS = ("tp", "fp", "fn", "tn")


def threshold_candidates() -> list[tuple[str, SpectralConfig]]:
    """Return every candidate in deterministic grid order for stable tie-breaking."""
    candidates = [
        ("hardcoded", SpectralConfig(mode="hardcoded", ndvi_drop=ndvi_drop, ndbi_rise=ndbi_rise, use_cloud_mask=False))
        for ndvi_drop in HARDCODED_NDVI_GRID
        for ndbi_rise in HARDCODED_NDBI_GRID
    ]
    candidates += [
        ("percentile", SpectralConfig(mode="percentile", percentile=percentile, use_cloud_mask=False))
        for percentile in PERCENTILE_GRID
    ]
    return candidates


def config_record(config: SpectralConfig) -> dict:
    if config.mode == "hardcoded":
        return {
            "mode": "hardcoded",
            "ndvi_drop": config.ndvi_drop,
            "ndbi_rise": config.ndbi_rise,
            "use_cloud_mask": config.use_cloud_mask,
        }
    if config.mode == "percentile":
        return {
            "mode": "percentile",
            "percentile": config.percentile,
            "use_cloud_mask": config.use_cloud_mask,
        }
    raise ValueError(f"LOCO supports hardcoded and percentile configs, got {config.mode}")


def _candidate_key(config: SpectralConfig) -> tuple:
    record = config_record(config)
    return tuple(record.get(name) for name in ("mode", "ndvi_drop", "ndbi_rise", "percentile", "use_cloud_mask"))


def validate_train_cities(train_cities: list[str], official_test_cities: tuple[str, ...] = OFFICIAL_TEST_CITIES) -> None:
    if not train_cities:
        raise ValueError("train.txt is empty")
    duplicates = sorted(city for city, count in Counter(train_cities).items() if count > 1)
    if duplicates:
        raise ValueError(f"train.txt contains duplicate cities: {duplicates}")
    leaked = sorted(set(train_cities) & set(official_test_cities))
    if leaked:
        raise ValueError(f"Refusing to run: official test cities appear in train.txt: {leaked}")


def assert_training_label_path(labels_root: Path) -> None:
    if "test" in labels_root.name.lower():
        raise ValueError(f"Refusing to read a test-label path: {labels_root}")


def score_candidates(
    cities: list[dict],
    candidates: list[tuple[str, SpectralConfig]] | None = None,
    show_progress: bool = False,
) -> dict[str, list[dict]]:
    """Score every candidate on every training city, storing confusion counts only."""
    candidates = threshold_candidates() if candidates is None else candidates
    names = [city["city"] for city in cities]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate training city names")
    scored: dict[str, list[dict]] = OrderedDict((family, []) for family, _ in candidates)
    for family, config in candidates:
        counts_by_city = {}
        iterator = tqdm(cities, desc=f"Scoring {family} candidates", leave=False) if show_progress else cities
        for city in iterator:
            prediction, _ = spectral_prediction(city, config)
            row = metrics(prediction, city["mask"])
            counts_by_city[city["city"]] = {field: int(row[field]) for field in COUNT_FIELDS}
        scored[family].append({"family": family, "config": config_record(config), "counts": counts_by_city})
    return scored


def _pooled_counts(entry: dict, cities: list[str]) -> dict[str, int]:
    missing = [city for city in cities if city not in entry["counts"]]
    if missing:
        raise ValueError(f"{entry['config']} is missing cities: {missing}")
    return {field: sum(entry["counts"][city][field] for city in cities) for field in COUNT_FIELDS}


def _metrics_from_counts(counts: dict[str, int]) -> dict[str, float | int]:
    tp, fp, fn, tn = (counts[field] for field in COUNT_FIELDS)
    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
        "overall_accuracy": (tp + tn) / total if total else 0.0,
        "predicted_fraction": (tp + fp) / total if total else 0.0,
        "true_fraction": (tp + fn) / total if total else 0.0,
        **{field: int(counts[field]) for field in COUNT_FIELDS},
    }


def select_entry(entries: list[dict], cities: list[str]) -> dict:
    """Select the candidate with the highest pooled F1; ties keep grid order."""
    if not cities:
        raise ValueError("Cannot select a threshold without cities")
    scored = []
    for entry in entries:
        counts = _pooled_counts(entry, cities)
        scored.append((_metrics_from_counts(counts)["f1"], counts, entry))
    best_f1 = max(item[0] for item in scored)
    best_index = next(index for index, item in enumerate(scored) if item[0] == best_f1)
    tied = sum(1 for item in scored if item[0] == best_f1)
    return {
        "config": scored[best_index][2]["config"],
        "f1_on_selection_cities": best_f1,
        "pooled_counts_on_selection_cities": scored[best_index][1],
        "tied_candidates": tied,
    }


def _selected_edge_warning(entry: dict) -> str | None:
    record = entry["config"]
    config = SpectralConfig(**record)
    return grid_edge_warning(record["mode"], config)


def loco_analysis(scored: dict[str, list[dict]], cities: list[str]) -> dict:
    """Hold out one training city at a time and select thresholds on the other cities."""
    if len(cities) < 3:
        raise ValueError("Leave-one-city-out requires at least three training cities")
    if len(cities) != len(set(cities)):
        raise ValueError("Duplicate training city names")
    result = {}
    for family, entries in scored.items():
        if not entries:
            raise ValueError(f"No candidates for family {family}")
        folds = []
        for held_out in cities:
            training = [city for city in cities if city != held_out]
            selection = select_entry(entries, training)
            entry = next(item for item in entries if item["config"] == selection["config"])
            held_counts = entry["counts"][held_out]
            fold_metrics = _metrics_from_counts(held_counts)
            folds.append(
                {
                    "held_out_city": held_out,
                    "selected_config": selection["config"],
                    "selection_f1_on_other_cities": selection["f1_on_selection_cities"],
                    "tied_candidates": selection["tied_candidates"],
                    "grid_edge_warning": _selected_edge_warning(entry),
                    "held_out_counts": held_counts,
                    "held_out_metrics": fold_metrics,
                }
            )
        pooled_held_out = {field: sum(fold["held_out_counts"][field] for fold in folds) for field in COUNT_FIELDS}
        frequencies = Counter(json.dumps(fold["selected_config"], sort_keys=True) for fold in folds)
        frequency_rows = [
            {"config": json.loads(config), "count": count, "held_out_cities": [fold["held_out_city"] for fold in folds if json.dumps(fold["selected_config"], sort_keys=True) == config]}
            for config, count in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))
        ]
        full_selection = select_entry(entries, cities)
        full_entry = next(item for item in entries if item["config"] == full_selection["config"])
        full_counts = _pooled_counts(full_entry, cities)
        result[family] = {
            "folds": folds,
            "pooled_held_out": _metrics_from_counts(pooled_held_out),
            "selected_config_frequencies": frequency_rows,
            "distinct_selected_configs": len(frequencies),
            "folds_with_grid_edge_warning": sum(1 for fold in folds if fold["grid_edge_warning"]),
            "full_train_selection": {
                "config": full_selection["config"],
                "grid_edge_warning": _selected_edge_warning(full_entry),
                "tied_candidates": full_selection["tied_candidates"],
                "pooled_f1_on_train_cities_in_sample": _metrics_from_counts(full_counts)["f1"],
            },
        }
    return result


def build_report(
    images: Path,
    train_labels: Path,
    *,
    train_cities: list[str] | None = None,
    candidates: list[tuple[str, SpectralConfig]] | None = None,
    show_progress: bool = True,
) -> dict:
    candidates = threshold_candidates() if candidates is None else candidates
    assert_training_label_path(train_labels)
    train_list = images / "train.txt"
    train_cities = read_city_list(train_list) if train_cities is None else train_cities
    validate_train_cities(train_cities)
    loading = tqdm(train_cities, desc="Loading training cities") if show_progress else train_cities
    training = [load_city(images, train_labels, city) for city in loading]
    scored = score_candidates(training, candidates=candidates, show_progress=show_progress)
    analysis = loco_analysis(scored, train_cities)
    return {
        "generated": date.today().isoformat(),
        "scope": "training cities and training labels only; no test labels read",
        "result_status": "computed_on_training_cities_only",
        "source": {
            "images_root": str(images),
            "train_labels_root": str(train_labels),
            "train_list": str(train_list),
            "train_list_sha256": hashlib.sha256(train_list.read_bytes()).hexdigest(),
            "train_cities": train_cities,
        },
        "guards": {
            "official_test_cities": list(OFFICIAL_TEST_CITIES),
            "official_test_cities_in_train_list": sorted(set(train_cities) & set(OFFICIAL_TEST_CITIES)),
            "test_labels_path_accepted": False,
        },
        "grids": {
            "hardcoded_ndvi_drop": list(HARDCODED_NDVI_GRID),
            "hardcoded_ndbi_rise": list(HARDCODED_NDBI_GRID),
            "percentile": list(PERCENTILE_GRID),
            "candidate_count": len(candidates),
        },
        "protocol": {
            "selection": "For each held-out training city, choose the candidate with the highest pooled F1 over the other training cities.",
            "evaluation": "Apply the selected candidate to the held-out training city.",
            "tie_breaking": "Highest pooled F1; ties keep the order of the candidate grids.",
            "otsu_included": False,
            "otsu_reason": "Otsu computes a threshold per city from that city's own histogram and has no train-selected global threshold.",
        },
        "families": analysis,
        "caveats": [
            "This is a training-split robustness check, not a test-set result.",
            "Scores use the same ten official test cities nowhere in this script; no test label is read.",
            "The held-out city is still a training city; its labels inform no selection in that fold.",
            "Full-train pooled F1 is in-sample and optimistic; it is reported only to show which configuration the grid selects.",
            "Otsu is excluded because it has no train-selected threshold to leave out.",
        ],
    }


def _print_summary(report: dict, output: Path) -> None:
    print(f"train cities={len(report['source']['train_cities'])} candidates={report['grids']['candidate_count']}")
    for family, values in report["families"].items():
        pooled = values["pooled_held_out"]
        print(
            f"{family}: LOCO pooled F1={pooled['f1']:.4f} IoU={pooled['iou']:.4f} "
            f"precision={pooled['precision']:.4f} recall={pooled['recall']:.4f} "
            f"distinct={values['distinct_selected_configs']} edge_folds={values['folds_with_grid_edge_warning']}"
        )
        print(f"{family}: full-train config={json.dumps(values['full_train_selection']['config'], sort_keys=True)}")
    print(f"wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/content/oscd"))
    parser.add_argument("--images-root", type=Path)
    parser.add_argument("--train-labels-root", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/results/oscd_loco_thresholds.json")
    args = parser.parse_args()
    images = args.images_root or args.root / "images" / "Onera Satellite Change Detection dataset - Images"
    train_labels = args.train_labels_root or args.root / "train_labels" / "Onera Satellite Change Detection dataset - Train Labels"
    report = build_report(images, train_labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    _print_summary(report, args.output)


if __name__ == "__main__":
    main()
