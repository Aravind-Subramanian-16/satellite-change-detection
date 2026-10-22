#!/usr/bin/env python3
"""Derive baselines, uncertainty and failure summaries from saved OSCD results.

This script never reads imagery and never scores a test city. It only reads the
saved per-city confusion counts in oscd_results_v2.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter, OrderedDict
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.oscd_eval import OFFICIAL_TEST_CITIES  # noqa: E402

METHODS = OrderedDict(
    [
        ("hardcoded", {"label": "Hardcoded NDVI/NDBI", "pipeline": "spectral", "configuration": "hardcoded"}),
        ("percentile", {"label": "Percentile 99.0", "pipeline": "spectral", "configuration": "percentile"}),
        ("otsu", {"label": "Otsu", "pipeline": "spectral", "configuration": "otsu"}),
        ("cnn_joint", {"label": "CNN joint-percentile", "pipeline": "cnn", "preprocess": "joint_percentile"}),
        ("cnn_reflectance", {"label": "CNN reflectance", "pipeline": "cnn", "preprocess": "reflectance"}),
    ]
)
METRIC_FIELDS = ("precision", "recall", "f1", "iou", "overall_accuracy", "predicted_fraction", "true_fraction")
COUNT_FIELDS = ("tp", "fp", "fn", "tn")


def compute_metrics(tp: float, fp: float, fn: float, tn: float) -> dict[str, float]:
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
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
    }


def classify_method(row: dict) -> str:
    if row.get("pipeline") == "spectral" and row.get("configuration") in {"hardcoded", "percentile", "otsu"}:
        return row["configuration"]
    if row.get("pipeline") == "cnn":
        preprocess = row.get("preprocess")
        if preprocess == "joint_percentile":
            return "cnn_joint"
        if preprocess == "reflectance":
            return "cnn_reflectance"
    raise ValueError(f"Unknown method identity: {row.get('pipeline')}/{row.get('configuration')}/{row.get('preprocess')}")


def load_results(path: Path, expected_cities: tuple[str, ...] | None = None) -> dict[str, dict[str, dict]]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list):
        raise ValueError("Results JSON must be a list")
    rows = [row for row in raw if row.get("record_type") != "run_metadata"]
    by_method: dict[str, dict[str, dict]] = OrderedDict((name, {}) for name in METHODS)
    for row in rows:
        if row.get("split") != "test":
            raise ValueError("Evidence may use test results only")
        name = classify_method(row)
        city = row.get("city")
        if not city:
            raise ValueError("Result row is missing city")
        if city in by_method[name]:
            raise ValueError(f"Duplicate result for {city}/{name}")
        metrics = row.get("metrics") or {}
        missing = [key for key in COUNT_FIELDS + METRIC_FIELDS if key not in metrics]
        if missing:
            raise ValueError(f"{city}/{name} missing metrics: {missing}")
        calculated = compute_metrics(*(metrics[key] for key in COUNT_FIELDS))
        for key in METRIC_FIELDS:
            if abs(float(metrics[key]) - calculated[key]) > 1e-6:
                raise ValueError(f"{city}/{name} saved {key} does not match confusion counts")
        by_method[name][city] = row
    cities = sorted({city for method in by_method.values() for city in method})
    if expected_cities is not None and tuple(cities) != tuple(sorted(expected_cities)):
        raise ValueError(f"Expected official test cities {sorted(expected_cities)}, got {cities}")
    if len(cities) < 2:
        raise ValueError("At least two cities are required")
    for name in METHODS:
        missing = sorted(set(cities) - set(by_method[name]))
        if missing:
            raise ValueError(f"Missing {name} rows for cities: {missing}")
        extra = sorted(set(by_method[name]) - set(cities))
        if extra:
            raise ValueError(f"Unexpected {name} rows: {extra}")
    return by_method


def pooled(rows: dict[str, dict]) -> dict[str, float]:
    counts = {field: sum(row["metrics"][field] for row in rows.values()) for field in COUNT_FIELDS}
    return compute_metrics(*(counts[field] for field in COUNT_FIELDS))


def baseline_summary(metrics: dict[str, float]) -> dict[str, dict[str, float]]:
    total = metrics["tp"] + metrics["fp"] + metrics["fn"] + metrics["tn"]
    true_pixels = metrics["tp"] + metrics["fn"]
    no_change = compute_metrics(0, 0, true_pixels, total - true_pixels)
    prevalence = true_pixels / total if total else 0.0
    random_expected = {
        "precision": prevalence,
        "recall": prevalence,
        "f1": prevalence,
        "iou": prevalence / (2 - prevalence) if prevalence < 2 else 0.0,
        "predicted_fraction": prevalence,
        "true_fraction": prevalence,
    }
    return {"all_no_change": no_change, "random_at_prevalence": random_expected}


def rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2 + 1
        start = end
    return ranks


def pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def correlations(per_city: list[dict]) -> dict[str, float | None]:
    true_fraction = np.array([row["true_fraction"] for row in per_city])
    f1 = np.array([row["f1"] for row in per_city])
    predicted_fraction = np.array([row["predicted_fraction"] for row in per_city])
    return {
        "true_fraction_vs_f1_pearson": pearson(true_fraction, f1),
        "true_fraction_vs_f1_spearman": pearson(rankdata(true_fraction), rankdata(f1)),
        "true_fraction_vs_predicted_fraction_pearson": pearson(true_fraction, predicted_fraction),
    }


def bootstrap_counts(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray, tn: np.ndarray, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    f1 = np.empty(len(indices), dtype=float)
    iou = np.empty(len(indices), dtype=float)
    for i, sample in enumerate(indices):
        metrics = compute_metrics(tp[sample].sum(), fp[sample].sum(), fn[sample].sum(), tn[sample].sum())
        f1[i] = metrics["f1"]
        iou[i] = metrics["iou"]
    return f1, iou


def interval(values: np.ndarray) -> list[float]:
    low, high = np.percentile(values, (2.5, 97.5))
    return [float(low), float(high)]


def bootstrap_summary(by_method: dict[str, dict[str, dict]], seed: int = 0, resamples: int = 10_000) -> dict:
    cities = sorted({city for method in by_method.values() for city in method})
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(cities), size=(resamples, len(cities)))
    arrays = {}
    for name, rows in by_method.items():
        arrays[name] = {field: np.array([rows[city]["metrics"][field] for city in cities], dtype=float) for field in COUNT_FIELDS}
    estimates = {}
    for name, values in arrays.items():
        f1, iou = bootstrap_counts(values["tp"], values["fp"], values["fn"], values["tn"], indices)
        base = pooled(by_method[name])
        estimates[name] = {
            "f1": {"point": base["f1"], "ci95": interval(f1), "resample_fraction_zero": float(np.mean(f1 == 0))},
            "iou": {"point": base["iou"], "ci95": interval(iou), "resample_fraction_zero": float(np.mean(iou == 0))},
        }
    hard = arrays["hardcoded"]
    hard_f1, hard_iou = bootstrap_counts(hard["tp"], hard["fp"], hard["fn"], hard["tn"], indices)
    for name, values in arrays.items():
        if name == "hardcoded":
            continue
        f1, iou = bootstrap_counts(values["tp"], values["fp"], values["fn"], values["tn"], indices)
        f1_diff, iou_diff = f1 - hard_f1, iou - hard_iou
        estimates[name]["paired_vs_hardcoded"] = {
            "f1": {
                "point": pooled(by_method[name])["f1"] - pooled(by_method["hardcoded"])["f1"],
                "ci95": interval(f1_diff),
                "fraction_resamples_positive": float(np.mean(f1_diff > 0)),
                "fraction_resamples_zero": float(np.mean(f1_diff == 0)),
            },
            "iou": {
                "point": pooled(by_method[name])["iou"] - pooled(by_method["hardcoded"])["iou"],
                "ci95": interval(iou_diff),
                "fraction_resamples_positive": float(np.mean(iou_diff > 0)),
                "fraction_resamples_zero": float(np.mean(iou_diff == 0)),
            },
        }
    return {
        "seed": seed,
        "resamples": resamples,
        "n_cities": len(cities),
        "cities": cities,
        "interval": "percentile 2.5-97.5",
        "paired_against": "hardcoded",
        "methods": estimates,
    }


def per_city_summary(by_method: dict[str, dict[str, dict]]) -> dict[str, list[dict]]:
    result = {}
    for name, rows in by_method.items():
        cities = sorted(rows)
        values = []
        for city in cities:
            metrics = rows[city]["metrics"]
            baseline = baseline_summary(metrics)["random_at_prevalence"]
            values.append(
                {
                    "city": city,
                    "true_fraction": metrics["true_fraction"],
                    "predicted_fraction": metrics["predicted_fraction"],
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "f1": metrics["f1"],
                    "iou": metrics["iou"],
                    "overall_accuracy": metrics["overall_accuracy"],
                    "random_f1": baseline["f1"],
                    "f1_minus_random": metrics["f1"] - baseline["f1"],
                }
            )
        result[name] = values
    return result


def failure_summary(by_method: dict[str, dict[str, dict]], per_city: dict[str, list[dict]]) -> dict:
    correlations_by_method = {name: correlations(rows) for name, rows in per_city.items()}
    prediction_balance = {}
    for name, rows in per_city.items():
        under = [row["city"] for row in rows if row["predicted_fraction"] < row["true_fraction"]]
        over = [row["city"] for row in rows if row["predicted_fraction"] > row["true_fraction"]]
        equal = [row["city"] for row in rows if row["predicted_fraction"] == row["true_fraction"]]
        prediction_balance[name] = {"under": under, "over": over, "equal": equal}
    cnn_empty = {}
    for name in ("cnn_joint", "cnn_reflectance"):
        cnn_empty[name] = [
            city for city, row in by_method[name].items() if row["metrics"]["tp"] + row["metrics"]["fp"] == 0
        ]
    otsu_rows = by_method["otsu"]
    otsu = {
        "pooled": pooled(otsu_rows),
        "predicted_fraction_range": [
            min(row["metrics"]["predicted_fraction"] for row in otsu_rows.values()),
            max(row["metrics"]["predicted_fraction"] for row in otsu_rows.values()),
        ],
        "ndvi_drop_thresholds": sorted({round(row["thresholds"]["ndvi_drop_threshold"], 6) for row in otsu_rows.values() if "thresholds" in row}),
        "ndbi_rise_thresholds": sorted({round(row["thresholds"]["ndbi_rise_threshold"], 6) for row in otsu_rows.values() if "thresholds" in row}),
        "over_predicted_cities": [row["city"] for row in per_city["otsu"] if row["predicted_fraction"] > row["true_fraction"]],
    }
    if otsu["ndvi_drop_thresholds"]:
        otsu["ndvi_drop_threshold_median"] = statistics.median(otsu["ndvi_drop_thresholds"])
    if otsu["ndbi_rise_thresholds"]:
        otsu["ndbi_rise_threshold_median"] = statistics.median(otsu["ndbi_rise_thresholds"])
    return {
        "correlations": correlations_by_method,
        "prediction_balance": prediction_balance,
        "cnn_zero_prediction_cities": cnn_empty,
        "otsu": otsu,
        "notes": [
            "Correlations use the ten test cities and are descriptive only.",
            "No causal relationship between city change prevalence and method F1 is claimed.",
            "The random baseline is an analytic expectation at each city's true change fraction.",
        ],
    }


def pipeline_spec() -> dict:
    return {
        "oscd_bands_read": ["B02", "B03", "B04", "B08", "B11"],
        "indices": {
            "ndvi": "(B08 - B04) / max(B08 + B04, 1e-6)",
            "ndbi": "(B11 - B08) / max(B11 + B08, 1e-6)",
            "differences": "after minus before",
        },
        "cnn_input": {
            "bands": ["B04", "B03", "B02"],
            "reflectance_scaling": "clip(raw / 10000 * 255, 0, 255) as uint8",
            "joint_percentile_scaling": "2nd and 98th percentiles over both dates combined; clip((raw - low) * 255 / (high - low), 0, 255)",
            "normalization": "divide by 255, then ImageNet mean [0.485,0.456,0.406], std [0.229,0.224,0.225]",
            "tiling": "256x256 tiles, 32-pixel overlap, edge padding, averaged probabilities",
            "scene_resize": False,
            "decision_threshold": 0.5,
        },
        "degradation": {
            "factors": [1, 2, 4, 8, 16, 20],
            "target_resolutions_m": [0.5, 1, 2, 4, 8, 10],
            "gaussian_blur": "PIL ImageFilter.GaussianBlur(radius=factor/2); no explicit kernel size",
            "blur_radius_px": {"2": 1.0, "4": 2.0, "8": 4.0, "16": 8.0, "20": 10.0},
            "downsample": "PIL LANCZOS to (width // factor, height // factor)",
            "upsample": "PIL LANCZOS back to 256x256",
            "intermediate_size_px": {"2": "128x128", "4": "64x64", "8": "32x32", "16": "16x16", "20": "12x12"},
            "normalization": "ImageNet mean/std, same as training",
            "decision_threshold": 0.5,
        },
        "metric_aggregation": "pooled TP/FP/FN/TN (micro), not mean of per-image metrics",
        "code_references": [
            "benchmarks/oscd_eval.py:27-32",
            "benchmarks/oscd_eval.py:41-55",
            "benchmarks/oscd_eval.py:77-96",
            "benchmarks/oscd_eval.py:133-152",
            "benchmarks/oscd_eval.py:206-213",
            "app.py:366-381",
            "tiling.py:6-25",
            "evaluate_degradation.py:19-31",
            "evaluate_degradation.py:76-116",
            "spectral_pipeline.py:63-87",
        ],
    }


def build_evidence(path: Path, seed: int = 0, resamples: int = 10_000, expected_cities: tuple[str, ...] | None = None) -> dict:
    source_path = Path(path).resolve()
    by_method = load_results(source_path, expected_cities=expected_cities)
    per_city = per_city_summary(by_method)
    pooled_by_method = {name: pooled(rows) for name, rows in by_method.items()}
    try:
        display_path = source_path.relative_to(ROOT).as_posix()
    except ValueError:
        display_path = source_path.as_posix()
    return {
        "source": {
            "path": display_path,
            "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "bytes": source_path.stat().st_size,
        },
        "generated": date.today().isoformat(),
        "scope": "saved per-city test confusion counts only; no re-scoring",
        "cities": sorted({city for rows in by_method.values() for city in rows}),
        "pooled": pooled_by_method,
        "baselines": {name: baseline_summary(metrics) for name, metrics in pooled_by_method.items()},
        "per_city": per_city,
        "bootstrap": bootstrap_summary(by_method, seed=seed, resamples=resamples),
        "failure": failure_summary(by_method, per_city),
        "pipeline_spec": pipeline_spec(),
        "caveats": [
            "Bootstrap intervals reflect sampling of the ten test cities only.",
            "Pixel-level and model-training uncertainty are not included.",
            "The random baseline is an expectation, not a run.",
            "The CNN reflectance row has no predicted positives in any test city.",
            "No causal claim is made from the city-level correlations.",
        ],
    }


def _pct(value: float) -> str:
    return f"{100 * value:.2f}"


def render_markdown(evidence: dict) -> str:
    lines = [
        "# OSCD evidence from saved v2 results",
        "",
        f"Generated: {evidence['generated']}  ",
        f"Source: `{evidence['source']['path']}` (SHA-256 `{evidence['source']['sha256']}`, {evidence['source']['bytes']} bytes)  ",
        f"Scope: {evidence['scope']}",
        "",
        "## Pooled test results",
        "",
        "The random baseline is the analytic expectation for a predictor that marks each pixel changed with probability equal to the true change fraction. The all-no-change predictor has F1 = 0 by definition.",
        "",
        "| Method | True change % | Predicted % | Precision | Recall | F1 | IoU | OA | All-no-change F1 | Random expected F1 | F1 - random |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, meta in METHODS.items():
        metrics = evidence["pooled"][name]
        baseline = evidence["baselines"][name]["random_at_prevalence"]
        lines.append(
            f"| {meta['label']} | {_pct(metrics['true_fraction'])} | {_pct(metrics['predicted_fraction'])} | "
            f"{metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['f1']:.4f} | {metrics['iou']:.4f} | "
            f"{metrics['overall_accuracy']:.4f} | 0.0000 | {baseline['f1']:.4f} | {metrics['f1'] - baseline['f1']:+.4f} |"
        )
    lines += [
        "",
        "## Per-city results",
        "",
        "Each method uses the same ten test cities and the same labels. `Random F1` is the expected F1 at that city's true change fraction.",
        "",
    ]
    for name, meta in METHODS.items():
        lines += [
            f"### {meta['label']}",
            "",
            "| City | True change % | Predicted % | F1 | IoU | Random F1 | F1 - random |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in evidence["per_city"][name]:
            lines.append(
                f"| {row['city']} | {_pct(row['true_fraction'])} | {_pct(row['predicted_fraction'])} | "
                f"{row['f1']:.4f} | {row['iou']:.4f} | {row['random_f1']:.4f} | {row['f1_minus_random']:+.4f} |"
            )
        lines.append("")
    boot = evidence["bootstrap"]
    lines += [
        "## City-level bootstrap",
        "",
        f"Seed {boot['seed']}; {boot['resamples']:,} resamples of the {boot['n_cities']} cities with replacement; "
        f"{boot['interval']} percentile intervals. Intervals reflect city sampling only.",
        "",
        "| Method | F1 | F1 95% CI | IoU | IoU 95% CI | Delta F1 vs hardcoded | Delta F1 95% CI | P(Delta F1 > 0) |",
        "|---|---:|---|---:|---|---:|---|---:|",
    ]
    for name, meta in METHODS.items():
        estimate = boot["methods"][name]
        paired = estimate.get("paired_vs_hardcoded")
        if paired:
            delta = f"{paired['f1']['point']:+.4f}"
            delta_ci = f"[{paired['f1']['ci95'][0]:+.4f}, {paired['f1']['ci95'][1]:+.4f}]"
            frac = f"{paired['f1']['fraction_resamples_positive']:.3f}"
        else:
            delta, delta_ci, frac = "reference", "-", "-"
        lines.append(
            f"| {meta['label']} | {estimate['f1']['point']:.4f} | "
            f"[{estimate['f1']['ci95'][0]:.4f}, {estimate['f1']['ci95'][1]:.4f}] | "
            f"{estimate['iou']['point']:.4f} | [{estimate['iou']['ci95'][0]:.4f}, {estimate['iou']['ci95'][1]:.4f}] | "
            f"{delta} | {delta_ci} | {frac} |"
        )
    lines += ["", "## Failure analysis", "", "### Correlations across ten cities", "", "| Method | Pearson r (true fraction, F1) | Spearman rho | Pearson r (true fraction, predicted fraction) |", "|---|---:|---:|---:|"]
    for name, meta in METHODS.items():
        corr = evidence["failure"]["correlations"][name]
        def value(key):
            item = corr[key]
            return "undefined (constant)" if item is None else f"{item:.3f}"
        lines.append(f"| {meta['label']} | {value('true_fraction_vs_f1_pearson')} | {value('true_fraction_vs_f1_spearman')} | {value('true_fraction_vs_predicted_fraction_pearson')} |")
    lines += [
        "",
        "These are descriptive statistics for ten cities; they do not identify a cause.",
        "",
        "### Prediction balance",
        "",
        "| Method | Cities under true fraction | Cities over true fraction | Cities equal |",
        "|---|---|---|---|",
    ]
    for name, meta in METHODS.items():
        balance = evidence["failure"]["prediction_balance"][name]
        lines.append(
            f"| {meta['label']} | {len(balance['under'])} ({', '.join(balance['under']) or 'none'}) | "
            f"{len(balance['over'])} ({', '.join(balance['over']) or 'none'}) | {len(balance['equal'])} |"
        )
    cnn = evidence["failure"]["cnn_zero_prediction_cities"]
    otsu = evidence["failure"]["otsu"]
    lines += [
        "",
        "### CNN and Otsu observations",
        "",
        f"- CNN joint-percentile predicted zero change pixels in {len(cnn['cnn_joint'])} of 10 cities: {', '.join(cnn['cnn_joint']) or 'none'}.",
        f"- CNN reflectance predicted zero change pixels in {len(cnn['cnn_reflectance'])} of 10 cities.",
        f"- Otsu predicted more than the true change fraction in {len(otsu['over_predicted_cities'])} of 10 cities; "
        f"pooled predicted fraction {_pct(otsu['pooled']['predicted_fraction'])}% versus {_pct(otsu['pooled']['true_fraction'])}% true; "
        f"pooled precision {otsu['pooled']['precision']:.4f}, recall {otsu['pooled']['recall']:.4f}, OA {otsu['pooled']['overall_accuracy']:.4f}.",
        f"- Otsu predicted fraction ranges from {_pct(otsu['predicted_fraction_range'][0])}% to {_pct(otsu['predicted_fraction_range'][1])}% across cities.",
        "",
        "The Otsu result is consistent with its per-city thresholds marking a large share of pixels changed; the saved data support the prediction-volume explanation, not a causal account.",
        "",
        "## Pipeline specification",
        "",
        "Read from code, not inferred:",
        "",
        f"- OSCD bands read: {', '.join(evidence['pipeline_spec']['oscd_bands_read'])}.",
        f"- NDVI: `{evidence['pipeline_spec']['indices']['ndvi']}`; NDBI: `{evidence['pipeline_spec']['indices']['ndbi']}`; differences are after minus before.",
        f"- CNN RGB input: {', '.join(evidence['pipeline_spec']['cnn_input']['bands'])}. Reflectance: `{evidence['pipeline_spec']['cnn_input']['reflectance_scaling']}`. Joint percentile: {evidence['pipeline_spec']['cnn_input']['joint_percentile_scaling']}.",
        f"- Tiling: {evidence['pipeline_spec']['cnn_input']['tiling']}; scene resize: {evidence['pipeline_spec']['cnn_input']['scene_resize']}; threshold {evidence['pipeline_spec']['cnn_input']['decision_threshold']}.",
        f"- Degradation: {evidence['pipeline_spec']['degradation']['gaussian_blur']}; downsample {evidence['pipeline_spec']['degradation']['downsample']}; upsample {evidence['pipeline_spec']['degradation']['upsample']}; threshold {evidence['pipeline_spec']['degradation']['decision_threshold']}.",
        "",
        "| Factor | Target resolution | Blur radius (px) | Intermediate size |",
        "|---:|---:|---:|---:|",
    ]
    for factor, resolution, radius, size in zip(
        evidence["pipeline_spec"]["degradation"]["factors"],
        evidence["pipeline_spec"]["degradation"]["target_resolutions_m"],
        ["0", "1.0", "2.0", "4.0", "8.0", "10.0"],
        ["256x256", "128x128", "64x64", "32x32", "16x16", "12x12"],
    ):
        lines.append(f"| {factor} | {resolution} m | {radius} | {size} |")
    lines += [
        "",
        f"- Metric aggregation: {evidence['pipeline_spec']['metric_aggregation']}.",
        "",
        "Code references: " + ", ".join(f"`{ref}`" for ref in evidence["pipeline_spec"]["code_references"]) + ".",
        "",
        "## Caveats",
        "",
    ]
    lines += [f"- {item}" for item in evidence["caveats"]]
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "benchmarks/results/oscd_results_v2.json")
    parser.add_argument("--json-output", type=Path, default=ROOT / "benchmarks/results/oscd_evidence.json")
    parser.add_argument("--md-output", type=Path, default=ROOT / "benchmarks/results/oscd_evidence.md")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--allow-nonofficial-cities", action="store_true", help="testing only; do not use for the official results")
    args = parser.parse_args()
    expected = None if args.allow_nonofficial_cities else OFFICIAL_TEST_CITIES
    evidence = build_evidence(args.input, seed=args.seed, resamples=args.resamples, expected_cities=expected)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(evidence, indent=2) + "\n")
    args.md_output.write_text(render_markdown(evidence))
    print(f"source_sha256={evidence['source']['sha256']}")
    print(f"cities={len(evidence['cities'])} bootstrap_seed={args.seed} resamples={args.resamples}")
    for name, meta in METHODS.items():
        metrics = evidence["pooled"][name]
        print(f"{name}: F1={metrics['f1']:.4f} IoU={metrics['iou']:.4f} predicted={100*metrics['predicted_fraction']:.2f}%")
    print(f"wrote {args.json_output}")
    print(f"wrote {args.md_output}")


if __name__ == "__main__":
    main()
