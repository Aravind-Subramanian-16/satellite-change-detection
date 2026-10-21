#!/usr/bin/env python3
"""Cross-validated component search on OSCD TRAIN cities only.

Every trial is logged, including failures. Selection is by pooled F1 on
leave-one-city-out validation folds. The official ten-city test split is never
loaded or scored here; the guard raises before any test raster is read.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from learned_features import OFFICIAL_TEST_CITIES, assert_no_test_cities
from postprocess import apply_mmu, morphological_cleanup
from radiometric import match_pair
from spectral_pipeline import SpectralConfig, detect_from_indices

HARD_TRIAL_BUDGET = 12
DEFAULT_SEED = 42
PIXEL_AREA_M2 = 100.0
MMU_HA = 0.5
NDVI_DROP_GRID = (-0.30, -0.20, -0.15, -0.10)
NDBI_RISE_GRID = (0.05, 0.10, 0.15, 0.20, 0.30)
PERCENTILE_GRID = (80.0, 85.0, 90.0, 95.0, 97.5, 98.0, 99.0, 99.5)


@dataclass(frozen=True)
class SystemSpec:
    name: str
    mode: str
    tune: bool
    pif: bool = False
    cleanup: bool = False
    mmu: bool = False

    @property
    def components(self) -> tuple[str, ...]:
        return tuple(
            name for name, enabled in (("pif", self.pif), ("cleanup", self.cleanup), ("mmu", self.mmu)) if enabled
        )


SYSTEMS = (
    SystemSpec("hardcoded_default", "hardcoded", False),
    SystemSpec("hardcoded_tuned", "hardcoded", True),
    SystemSpec("hardcoded_tuned+pif", "hardcoded", True, pif=True),
    SystemSpec("hardcoded_tuned+cleanup", "hardcoded", True, cleanup=True),
    SystemSpec("hardcoded_tuned+mmu", "hardcoded", True, mmu=True),
    SystemSpec("hardcoded_tuned+pif+cleanup", "hardcoded", True, pif=True, cleanup=True),
    SystemSpec("hardcoded_tuned+pif+mmu", "hardcoded", True, pif=True, mmu=True),
    SystemSpec("hardcoded_tuned+cleanup+mmu", "hardcoded", True, cleanup=True, mmu=True),
    SystemSpec("hardcoded_tuned+pif+cleanup+mmu", "hardcoded", True, pif=True, cleanup=True, mmu=True),
    SystemSpec("percentile_tuned", "percentile", True),
    SystemSpec("percentile_tuned+pif+cleanup+mmu", "percentile", True, pif=True, cleanup=True, mmu=True),
    SystemSpec("otsu", "otsu", False),
)
SYSTEM_LOOKUP = {spec.name: spec for spec in SYSTEMS}

ABLATION_PAIRS = {
    "pif": (
        ("hardcoded_tuned", "hardcoded_tuned+pif"),
        ("hardcoded_tuned+cleanup", "hardcoded_tuned+pif+cleanup"),
        ("hardcoded_tuned+mmu", "hardcoded_tuned+pif+mmu"),
        ("hardcoded_tuned+cleanup+mmu", "hardcoded_tuned+pif+cleanup+mmu"),
    ),
    "cleanup": (
        ("hardcoded_tuned", "hardcoded_tuned+cleanup"),
        ("hardcoded_tuned+pif", "hardcoded_tuned+pif+cleanup"),
        ("hardcoded_tuned+mmu", "hardcoded_tuned+cleanup+mmu"),
        ("hardcoded_tuned+pif+mmu", "hardcoded_tuned+pif+cleanup+mmu"),
    ),
    "mmu": (
        ("hardcoded_tuned", "hardcoded_tuned+mmu"),
        ("hardcoded_tuned+cleanup", "hardcoded_tuned+cleanup+mmu"),
        ("hardcoded_tuned+pif", "hardcoded_tuned+pif+mmu"),
        ("hardcoded_tuned+pif+cleanup", "hardcoded_tuned+pif+cleanup+mmu"),
    ),
}


class BudgetExceeded(RuntimeError):
    """More trials were requested than the fixed preregistered budget."""


def scores(prediction: np.ndarray, label: np.ndarray) -> dict:
    predicted, actual = np.asarray(prediction).astype(bool), np.asarray(label).astype(bool)
    if predicted.shape != actual.shape:
        raise ValueError("prediction and label shapes differ")
    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())
    tn = int((~predicted & ~actual).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    total = tp + fp + fn + tn
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
        "overall_accuracy": (tp + tn) / total if total else 0.0,
        "predicted_fraction": (tp + fp) / total if total else 0.0,
        "true_fraction": (tp + fn) / total if total else 0.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def pooled_scores(rows: list[dict]) -> dict:
    counts = {name: sum(int(row[name]) for row in rows) for name in ("tp", "fp", "fn", "tn")}
    tp, fp, fn, tn = counts["tp"], counts["fp"], counts["fn"], counts["tn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    total = tp + fp + fn + tn
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
        "overall_accuracy": (tp + tn) / total if total else 0.0,
        "predicted_fraction": (tp + fp) / total if total else 0.0,
        "true_fraction": (tp + fn) / total if total else 0.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def leave_city_out_folds(cities: list[str]) -> list[dict]:
    ordered = sorted(str(city) for city in cities)
    if len(set(ordered)) != len(ordered):
        raise ValueError("city list contains duplicates")
    if len(ordered) < 2:
        raise ValueError("leave-city-out validation needs at least two cities")
    assert_no_test_cities(ordered)
    return [
        {"fold": index, "validation": [city], "fit": [other for other in ordered if other != city]}
        for index, city in enumerate(ordered)
    ]


def _config(spec: SystemSpec, params: dict) -> SpectralConfig:
    return SpectralConfig(
        mode=spec.mode,
        ndvi_drop=float(params.get("ndvi_drop", -0.15)),
        ndbi_rise=float(params.get("ndbi_rise", 0.10)),
        percentile=float(params.get("percentile", 95.0)),
        use_cloud_mask=False,
    )


def predict_mask(data: dict, spec: SystemSpec, params: dict) -> np.ndarray:
    ndvi_b, ndbi_b = data["ndvi_b"], data["ndbi_b"]
    if spec.pif:
        ndvi_b = match_pair(data["ndvi_a"], ndvi_b)
        ndbi_b = match_pair(data["ndbi_a"], ndbi_b)
    mask, _, _ = detect_from_indices(
        data["ndvi_a"], data["ndbi_a"], ndvi_b, ndbi_b, config=_config(spec, params)
    )
    mask = np.asarray(mask, dtype=np.uint8)
    if spec.cleanup:
        mask = morphological_cleanup(mask, open_size=3, close_size=3)
    if spec.mmu:
        mask, _ = apply_mmu(mask, pixel_area_m2=PIXEL_AREA_M2, mmu_ha=MMU_HA)
    return mask


def candidate_params(spec: SystemSpec) -> list[dict]:
    if spec.mode == "hardcoded":
        if not spec.tune:
            return [{"ndvi_drop": -0.15, "ndbi_rise": 0.10}]
        return [
            {"ndvi_drop": ndvi, "ndbi_rise": ndbi}
            for ndvi in NDVI_DROP_GRID
            for ndbi in NDBI_RISE_GRID
        ]
    if spec.mode == "percentile":
        if not spec.tune:
            return [{"percentile": 95.0}]
        return [{"percentile": value} for value in PERCENTILE_GRID]
    if spec.mode == "otsu":
        return [{}]
    raise ValueError(f"Unknown mode: {spec.mode}")


def fit_params(spec: SystemSpec, fit_data: list[dict]) -> tuple[dict, dict]:
    """Select thresholds on fit-city pooled F1 only."""
    if not fit_data:
        raise ValueError("fit data is empty")
    candidates = candidate_params(spec)
    rows = []
    for params in candidates:
        metrics = [scores(predict_mask(data, spec, params), data["mask"]) for data in fit_data]
        summary = pooled_scores(metrics)
        rows.append({"params": params, **summary})
    if spec.mode == "hardcoded" and spec.tune:
        default = {"ndvi_drop": -0.15, "ndbi_rise": 0.10}
        best = max(
            rows,
            key=lambda row: (
                row["f1"],
                row["precision"],
                -abs(row["params"]["ndvi_drop"] - default["ndvi_drop"]),
                -abs(row["params"]["ndbi_rise"] - default["ndbi_rise"]),
            ),
        )
    elif spec.mode == "percentile" and spec.tune:
        best = max(rows, key=lambda row: (row["f1"], row["precision"], -abs(row["params"]["percentile"] - 95.0)))
    else:
        best = max(rows, key=lambda row: (row["f1"], row["precision"]))
    return dict(best["params"]), {"candidates": len(rows), "pooled_fit_f1": best["f1"], "pooled_fit_precision": best["precision"]}


def evaluate_trial(spec: SystemSpec, cities: list[str], get_data) -> dict:
    folds = leave_city_out_folds(cities)
    fold_rows = []
    for fold in folds:
        fit = [get_data(city) for city in fold["fit"]]
        validation_city = fold["validation"][0]
        params, fit_info = fit_params(spec, fit)
        data = get_data(validation_city)
        prediction = predict_mask(data, spec, params)
        fold_rows.append(
            {
                "fold": fold["fold"],
                "validation_city": validation_city,
                "fit_cities": fold["fit"],
                "selected_params": params,
                "fit_selection": fit_info,
                "metrics": scores(prediction, data["mask"]),
            }
        )
    pooled = pooled_scores([row["metrics"] for row in fold_rows])
    per_city_f1 = [row["metrics"]["f1"] for row in fold_rows]
    return {
        "status": "ok",
        "components": list(spec.components),
        "folds": fold_rows,
        "fit_choices": sorted({json.dumps(row["selected_params"], sort_keys=True) for row in fold_rows}),
        "summary": {
            "pooled_out_of_fold": pooled,
            "mean_f1": float(np.mean(per_city_f1)),
            "std_f1": float(np.std(per_city_f1, ddof=1)) if len(per_city_f1) > 1 else 0.0,
            "min_f1": float(np.min(per_city_f1)),
            "max_f1": float(np.max(per_city_f1)),
            "cities": len(fold_rows),
        },
    }


def _ablation_table(trials: dict[str, dict]) -> list[dict]:
    rows = []
    for component, pairs in ABLATION_PAIRS.items():
        deltas: list[float] = []
        pooled_deltas: list[float] = []
        available = 0
        for without_name, with_name in pairs:
            without, with_ = trials.get(without_name), trials.get(with_name)
            if not without or without.get("status") != "ok" or not with_ or with_.get("status") != "ok":
                continue
            available += 1
            without_f1 = {row["validation_city"]: row["metrics"]["f1"] for row in without["folds"]}
            with_f1 = {row["validation_city"]: row["metrics"]["f1"] for row in with_["folds"]}
            for city in sorted(set(without_f1) & set(with_f1)):
                deltas.append(with_f1[city] - without_f1[city])
            pooled_deltas.append(
                with_["summary"]["pooled_out_of_fold"]["f1"] - without["summary"]["pooled_out_of_fold"]["f1"]
            )
        rows.append(
            {
                "component": component,
                "pairs_available": available,
                "pairs_expected": len(pairs),
                "mean_delta_f1": float(np.mean(deltas)) if deltas else None,
                "std_delta_f1": float(np.std(deltas, ddof=1)) if len(deltas) > 1 else None,
                "mean_pooled_delta_f1": float(np.mean(pooled_deltas)) if pooled_deltas else None,
                "city_deltas": len(deltas),
                "decision": "kept" if deltas and float(np.mean(deltas)) > 0 else "dropped",
            }
        )
    return rows


def _select(trials: list[dict], ablation: list[dict]) -> tuple[dict, dict]:
    successful = [trial for trial in trials if trial.get("status") == "ok"]
    if not successful:
        return {"status": "no_successful_trials"}, {"status": "no_successful_trials"}
    selected = max(
        successful,
        key=lambda trial: (
            trial["summary"]["pooled_out_of_fold"]["f1"],
            trial["summary"]["pooled_out_of_fold"]["precision"],
            trial["summary"]["pooled_out_of_fold"]["recall"],
            -len(trial.get("components") or []),
        ),
    )
    kept = {row["component"] for row in ablation if row["decision"] == "kept"}
    eligible = [
        trial for trial in successful if set(trial.get("components") or []) <= kept
    ]
    recommendation = max(
        eligible,
        key=lambda trial: (
            trial["summary"]["pooled_out_of_fold"]["f1"],
            trial["summary"]["pooled_out_of_fold"]["precision"],
            -len(trial.get("components") or []),
        ),
    ) if eligible else None
    dropped = sorted({component for row in ablation if row["decision"] == "dropped" for component in [row["component"]]})
    return (
        {
            "status": "ok",
            "rule": "highest pooled out-of-fold F1; ties by precision, recall then fewer components",
            "system": selected["system"],
            "trial_id": selected["trial_id"],
            "pooled_out_of_fold": selected["summary"]["pooled_out_of_fold"],
            "mean_f1": selected["summary"]["mean_f1"],
            "std_f1": selected["summary"]["std_f1"],
        },
        {
            "status": "ok" if recommendation else "no_eligible_system",
            "rule": "highest pooled out-of-fold F1 among systems whose components were all kept by validation ablations",
            "system": recommendation["system"] if recommendation else None,
            "trial_id": recommendation["trial_id"] if recommendation else None,
            "dropped_components": dropped,
            "kept_components": sorted(kept),
        },
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _write_markdown(path: Path, payload: dict) -> None:
    metadata = payload["metadata"]
    lines = [
        "# Auto-improvement log (validation only)",
        "",
        f"Generated: {metadata['created_utc']}  ",
        f"Code commit: `{metadata['code_commit']}`  ",
        f"Seed: `{metadata['seed']}`  ",
        f"Scope: {metadata['scope']}  ",
        f"Trial budget: `{metadata['trial_budget']}` (attempted `{metadata['trials_attempted']}`)  ",
        "Official test cities read: **false**",
        "",
        "## Trials",
        "",
        "| System | Status | Pooled F1 | Precision | Recall | IoU | Mean city F1 ± SD | Predicted | True |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for trial in payload["trials"]:
        if trial.get("status") != "ok":
            lines.append(f"| {trial['system']} | failed | — | — | — | — | — | — | — |")
            continue
        value = trial["summary"]["pooled_out_of_fold"]
        mean = trial["summary"]["mean_f1"]
        std = trial["summary"]["std_f1"]
        lines.append(
            f"| {trial['system']} | ok | {value['f1']:.4f} | {value['precision']:.4f} | {value['recall']:.4f} | "
            f"{value['iou']:.4f} | {mean:.4f} ± {std:.4f} | {value['predicted_fraction'] * 100:.2f}% | "
            f"{value['true_fraction'] * 100:.2f}% |"
        )
    lines += [
        "",
        "## Validation ablation (paired held-out-city differences; positive = component helps)",
        "",
        "| Component | Pairs | Mean ΔF1 | SD ΔF1 | Mean pooled ΔF1 | Decision |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in payload["ablations"]:
        mean = "—" if row["mean_delta_f1"] is None else f"{row['mean_delta_f1']:.4f}"
        std = "—" if row["std_delta_f1"] is None else f"{row['std_delta_f1']:.4f}"
        pooled = "—" if row["mean_pooled_delta_f1"] is None else f"{row['mean_pooled_delta_f1']:.4f}"
        lines.append(
            f"| {row['component']} | {row['pairs_available']}/{row['pairs_expected']} | {mean} | {std} | {pooled} | {row['decision']} |"
        )
    selection = payload["selection"]
    recommendation = payload["recommendation"]
    lines += [
        "",
        "## Selection",
        "",
        f"- Validation-selected system: `{selection.get('system', 'none')}` "
        f"(pooled F1 {selection.get('pooled_out_of_fold', {}).get('f1', 0):.4f}, "
        f"mean city F1 {selection.get('mean_f1', 0):.4f} ± {selection.get('std_f1', 0):.4f}).",
        f"- Recommendation after dropping non-helping components: `{recommendation.get('system') or 'none'}`.",
        f"- Dropped components: {', '.join(recommendation.get('dropped_components') or []) or 'none'}.",
        f"- Final training-city fit: `{json.dumps(recommendation.get('final_fit', {}).get('params'), sort_keys=True)}`.",
        "",
        "This log contains held-out training-city results only. It is not a test-set result and must not be cited as one.",
        "",
    ]
    failures = [trial for trial in payload["trials"] if trial.get("status") != "ok"]
    if failures:
        lines += ["## Failures", ""]
        lines += [f"- `{trial['system']}`: {trial.get('error', 'unknown error')}" for trial in failures]
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def run_search(
    cities: list[str],
    loader,
    output: Path,
    *,
    systems: tuple[SystemSpec, ...] = SYSTEMS,
    max_trials: int = HARD_TRIAL_BUDGET,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Run the fixed search; checkpoint the log after every attempted trial."""
    assert_no_test_cities(cities)
    if len(set(cities)) != len(cities):
        raise ValueError("city list contains duplicates")
    if max_trials > HARD_TRIAL_BUDGET:
        raise BudgetExceeded(f"max_trials exceeds the hard budget of {HARD_TRIAL_BUDGET}")
    if len(systems) > max_trials:
        raise BudgetExceeded(f"{len(systems)} systems requested but the budget is {max_trials}")
    if any(city in OFFICIAL_TEST_CITIES for city in cities):
        raise ValueError("Official test cities are not allowed in training/validation")

    from provenance import get_commit_hash

    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "record_type": "auto_improve_log",
        "metadata": {
            "created_utc": created,
            "code_commit": get_commit_hash(),
            "seed": int(seed),
            "scope": "OSCD training cities only; leave-one-city-out validation folds",
            "cities": sorted(cities),
            "folds": len(cities),
            "trial_budget": int(max_trials),
            "trials_attempted": 0,
            "systems": [spec.name for spec in systems],
            "search_space": {
                "ndvi_drop_grid": list(NDVI_DROP_GRID),
                "ndbi_rise_grid": list(NDBI_RISE_GRID),
                "percentile_grid": list(PERCENTILE_GRID),
                "pixel_area_m2": PIXEL_AREA_M2,
                "mmu_ha": MMU_HA,
                "cleanup": "3x3 open then 3x3 close",
            },
            "official_test_cities_excluded": list(OFFICIAL_TEST_CITIES),
            "test_split_read": False,
            "complete": False,
        },
        "trials": [],
        "selection": {"status": "running"},
        "ablations": [],
        "recommendation": {"status": "running"},
    }
    cache: dict[str, dict] = {}

    def get_data(city: str) -> dict:
        if city not in cache:
            cache[city] = loader(city)
        return cache[city]

    for trial_id, spec in enumerate(systems, start=1):
        if payload["metadata"]["trials_attempted"] >= max_trials:
            raise BudgetExceeded(f"Trial budget of {max_trials} exhausted")
        payload["metadata"]["trials_attempted"] += 1
        started = time.perf_counter()
        trial = {"trial_id": trial_id, "system": spec.name, "status": "ok"}
        try:
            trial.update(evaluate_trial(spec, cities, get_data))
        except Exception as exc:  # every failure is logged, not hidden
            trial.update(
                {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                    "components": list(spec.components),
                }
            )
        trial["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["trials"].append(trial)
        available = {entry["system"]: entry for entry in payload["trials"]}
        payload["ablations"] = _ablation_table(available)
        payload["selection"], payload["recommendation"] = _select(payload["trials"], payload["ablations"])
        _write_json(output, payload)

    payload["metadata"]["complete"] = True
    recommendation = payload["recommendation"]
    if recommendation.get("status") == "ok":
        spec = next((entry for entry in systems if entry.name == recommendation["system"]), None)
        if spec is not None:
            try:
                final_params, final_info = fit_params(spec, [get_data(city) for city in cities])
            except Exception as exc:
                recommendation["final_fit"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            else:
                recommendation["final_fit"] = {
                    "status": "ok",
                    "params": final_params,
                    "selection": final_info,
                    "fit_cities": sorted(cities),
                    "note": "Fit on all 14 training cities; frozen before test scoring.",
                }
    _write_json(output, payload)
    _write_markdown(output.with_suffix(".md"), payload)
    return payload


def load_oscd_train_city(images_root: Path, train_labels_root: Path, city: str) -> dict:
    """Read only a training city (guard checked before any raster access)."""
    assert_no_test_cities([city])
    import oscd_eval

    mask, label_shape = oscd_eval.load_label(train_labels_root, city)
    arrays = {}
    for key, directory in (("a", "imgs_1_rect"), ("b", "imgs_2_rect")):
        root = images_root / city / directory
        bands = {band: oscd_eval.raster(oscd_eval.band_path(root, band)) for band in ("B04", "B08", "B11")}
        for band, array in bands.items():
            if array.shape != label_shape:
                raise ValueError(f"{city} {key} {band}: shape {array.shape} != label {label_shape}")
        arrays[key] = bands
    def indices(bands: dict) -> tuple[np.ndarray, np.ndarray]:
        red, nir, swir = bands["B04"], bands["B08"], bands["B11"]
        return (nir - red) / np.maximum(nir + red, 1e-6), (swir - nir) / np.maximum(swir + nir, 1e-6)
    ndvi_a, ndbi_a = indices(arrays["a"])
    ndvi_b, ndbi_b = indices(arrays["b"])
    return {"city": city, "mask": mask, "ndvi_a": ndvi_a, "ndbi_a": ndbi_a, "ndvi_b": ndvi_b, "ndbi_b": ndbi_b}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--train-labels-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results/auto_improve_log.json"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    split = args.images_root / "train.txt"
    if not split.is_file():
        raise FileNotFoundError(f"Missing training split: {split}")
    cities = [city.strip() for city in split.read_text().replace("\n", ",").split(",") if city.strip()]
    if len(cities) != 14:
        raise ValueError(f"Expected 14 training cities, found {len(cities)}")
    assert_no_test_cities(cities)
    print(f"Training cities ({len(cities)}): {', '.join(cities)}")
    print("Official test cities are excluded and are not read.")
    payload = run_search(
        cities,
        lambda city: load_oscd_train_city(args.images_root, args.train_labels_root, city),
        args.output,
        seed=args.seed,
    )
    selection = payload["selection"]
    print(f"Validation-selected system: {selection.get('system')} (pooled OOF F1 {selection.get('pooled_out_of_fold', {}).get('f1', 0):.4f})")
    print(f"Recommendation: {payload['recommendation'].get('system')}")
    print(f"Log: {args.output} and {args.output.with_suffix('.md')}")
    print("No test city was read; test scoring is a separate preregistered Phase D2.6 run.")


if __name__ == "__main__":
    main()
