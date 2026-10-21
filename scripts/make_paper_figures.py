"""Generate paper figures and LaTeX tables from saved benchmark JSON only.

No network access, no model inference and no invented values. Missing optional
logs produce clearly labelled placeholder figures/tables rather than estimates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

METHOD_ORDER = ("hardcoded", "percentile", "cnn_joint", "cnn_reflectance", "otsu")
METHOD_LABELS = {
    "hardcoded": "Spectral hardcoded",
    "percentile": "Spectral percentile",
    "cnn_joint": "CNN joint percentile",
    "cnn_reflectance": "CNN reflectance",
    "otsu": "Spectral Otsu",
}
COLORS = {
    "hardcoded": "#0072B2",
    "percentile": "#009E73",
    "cnn_joint": "#D55E00",
    "cnn_reflectance": "#CC79A7",
    "otsu": "#E69F00",
}
F1_METHODS = ("hardcoded", "percentile", "cnn_joint", "cnn_reflectance")
REPORTED_SCORE = {
    "hardcoded": "F1",
    "percentile": "F1",
    "cnn_joint": "F1",
    "cnn_reflectance": "F1",
    "otsu": "OA",
}
CITIES_EXPECTED = 10


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def method_key(row: dict) -> str:
    if row.get("pipeline") == "cnn":
        preprocess = row.get("preprocess")
        if preprocess == "joint_percentile":
            return "cnn_joint"
        if preprocess == "reflectance":
            return "cnn_reflectance"
        raise ValueError(f"Unknown CNN preprocess in results: {preprocess!r}")
    if row.get("pipeline") == "spectral":
        configuration = row.get("configuration")
        if configuration in {"hardcoded", "percentile", "otsu"}:
            return configuration
        raise ValueError(f"Unknown spectral configuration in results: {configuration!r}")
    raise ValueError(f"Unknown pipeline in results: {row.get('pipeline')!r}")


def load_results(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, list) or not data:
        raise ValueError(f"{path} must contain a non-empty JSON list of result rows")
    rows = []
    seen = set()
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"Row {index} is not an object")
        for key in ("city", "pipeline", "split", "metrics"):
            if key not in row:
                raise ValueError(f"Row {index} is missing {key!r}")
        if row["split"] != "test":
            raise ValueError(f"Row {index} is not a test row; paper figures use test results only")
        metrics = row["metrics"]
        for key in ("precision", "recall", "f1", "overall_accuracy", "predicted_fraction", "true_fraction", "tp", "fp", "fn", "tn"):
            if key not in metrics:
                raise ValueError(f"Row {index} metrics are missing {key!r}")
        identity = (row["city"], method_key(row))
        if identity in seen:
            raise ValueError(f"Duplicate result for city/method {identity}")
        seen.add(identity)
        rows.append(row)
    cities = {row["city"] for row in rows}
    for city in cities:
        present = {method_key(row) for row in rows if row["city"] == city}
        missing = set(METHOD_ORDER) - present
        if missing:
            raise ValueError(f"{city} is missing methods: {', '.join(sorted(missing))}")
    return rows


def _metric(row: dict, key: str) -> float:
    value = float(row["metrics"][key])
    if not np.isfinite(value):
        raise ValueError(f"Non-finite metric {key} for {row['city']}")
    return value


def pooled_metrics(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    tp = sum(int(row["metrics"]["tp"]) for row in rows)
    fp = sum(int(row["metrics"]["fp"]) for row in rows)
    fn = sum(int(row["metrics"]["fn"]) for row in rows)
    tn = sum(int(row["metrics"]["tn"]) for row in rows)
    total = tp + fp + fn + tn
    if total <= 0:
        raise ValueError("Pooled confusion counts are empty")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n_pixels": total,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "overall_accuracy": (tp + tn) / total,
        "predicted_fraction": (tp + fp) / total,
        "true_fraction": (tp + fn) / total,
    }


def _rows_by_method(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = {method: [] for method in METHOD_ORDER}
    for row in rows:
        grouped[method_key(row)].append(row)
    return grouped


def _style_axes(axis) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color="#dddddd", linewidth=0.6, zorder=0)


def plot_per_city_f1(rows: list[dict], output: Path) -> None:
    cities = sorted({row["city"] for row in rows})
    positions = np.arange(len(cities), dtype=float)
    width = 0.19
    figure, axis = plt.subplots(figsize=(7.2, 3.3))
    grouped = _rows_by_method(rows)
    for offset, method in enumerate(F1_METHODS):
        values = []
        for city in cities:
            match = next(row for row in grouped[method] if row["city"] == city)
            values.append(_metric(match, "f1"))
        axis.bar(
            positions + (offset - 1.5) * width,
            values,
            width=width,
            color=COLORS[method],
            label=METHOD_LABELS[method],
            zorder=2,
        )
    axis.set_xticks(positions, cities, rotation=30, ha="right")
    axis.set_ylabel("F1")
    axis.set_ylim(0, max(0.05, max(_metric(row, "f1") for row in rows) * 1.15))
    axis.legend(frameon=False, ncol=2, fontsize=7, loc="upper left")
    axis.set_title("Per-city F1 on the official OSCD test split (v2)", fontsize=9)
    _style_axes(axis)
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def plot_predicted_vs_true(rows: list[dict], output: Path) -> None:
    figure, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw={"width_ratios": [1, 1]})
    grouped = _rows_by_method(rows)
    for method in METHOD_ORDER:
        subset = grouped[method]
        true = [_metric(row, "true_fraction") * 100 for row in subset]
        predicted = [_metric(row, "predicted_fraction") * 100 for row in subset]
        left.scatter(true, predicted, s=20, color=COLORS[method], label=METHOD_LABELS[method], alpha=0.9)
        if method != "otsu":
            right.scatter(true, predicted, s=24, color=COLORS[method], alpha=0.9)
    limit = max([_metric(row, "true_fraction") * 100 for row in rows] + [12.0]) * 1.1
    right.plot([0, limit], [0, limit], color="#666666", linewidth=0.8, linestyle="--", label="predicted = true")
    left.plot([0, 12], [0, 12], color="#666666", linewidth=0.8, linestyle="--")
    left.set_yscale("symlog", linthresh=0.01)
    left.set_xlim(0, 11)
    left.set_ylim(0, 120)
    left.set_title("All methods (symlog y)", fontsize=8)
    right.set_xlim(0, limit)
    right.set_ylim(0, limit)
    right.set_title("Low range, Otsu excluded", fontsize=8)
    for axis in (left, right):
        axis.set_xlabel("True change (%)")
        axis.set_ylabel("Predicted change (%)")
        _style_axes(axis)
    left.legend(frameon=False, fontsize=6, loc="lower right")
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def plot_precision_recall(rows: list[dict], output: Path) -> None:
    cities = sorted({row["city"] for row in rows})
    figure, axis = plt.subplots(figsize=(4.4, 3.4))
    grouped = _rows_by_method(rows)
    for method in METHOD_ORDER:
        subset = grouped[method]
        axis.scatter(
            [_metric(row, "recall") for row in subset],
            [_metric(row, "precision") for row in subset],
            s=16,
            color=COLORS[method],
            alpha=0.55,
            edgecolor="none",
            label=f"{METHOD_LABELS[method]} (cities)",
        )
        pooled = pooled_metrics(subset)
        axis.scatter(
            [pooled["recall"]],
            [pooled["precision"]],
            s=110,
            marker="*",
            color=COLORS[method],
            edgecolor="black",
            linewidth=0.4,
            zorder=4,
        )
    axis.scatter([], [], marker="*", s=110, color="#555555", edgecolor="black", label="Pooled (stars)")
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.set_xlabel("Recall")
    axis.set_ylabel("Precision")
    axis.set_title(f"Per-city points and pooled stars ({len(cities)} cities)", fontsize=8)
    axis.legend(frameon=False, fontsize=5.5, loc="upper right")
    _style_axes(axis)
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def _placeholder(output: Path, title: str, message: str) -> None:
    figure, axis = plt.subplots(figsize=(5.2, 3.0))
    axis.axis("off")
    axis.text(0.5, 0.62, title, ha="center", va="center", fontsize=11, weight="bold")
    axis.text(0.5, 0.34, message, ha="center", va="center", fontsize=8.5, wrap=True)
    figure.savefig(output, dpi=200)
    plt.close(figure)


def plot_ablation(log_path: Path | None, output: Path) -> dict | None:
    if log_path is None or not log_path.is_file():
        _placeholder(
            output,
            "Validation ablation not run in this checkout",
            "No benchmarks/results/auto_improve_log.json was supplied.\n"
            "No synthetic or estimated values are plotted.",
        )
        return None
    payload = json.loads(log_path.read_text())
    rows = [row for row in payload.get("ablations", []) if row.get("mean_delta_f1") is not None]
    if not rows:
        _placeholder(output, "Validation ablation has no paired results", "The supplied log contains no paired component comparisons.")
        return payload
    labels = [row["component"] for row in rows]
    means = [float(row["mean_delta_f1"]) for row in rows]
    figure, axis = plt.subplots(figsize=(5.4, 2.9))
    axis.bar(range(len(rows)), means, color=["#009E73" if value >= 0 else "#D55E00" for value in means], zorder=2)
    axis.axhline(0, color="#444444", linewidth=0.8)
    axis.set_xticks(range(len(rows)), labels, rotation=25, ha="right")
    axis.set_ylabel("Mean paired ΔF1 (held-out train cities)")
    axis.set_title("Validation ablation from the supplied auto-improve log", fontsize=9)
    _style_axes(axis)
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)
    return payload


def plot_reliability(path: Path | None, output: Path) -> dict | None:
    if path is None or not path.is_file():
        _placeholder(
            output,
            "Reliability diagram not available",
            "No held-out-TRAIN calibration JSON was supplied.\nNo ECE or calibration curve is inferred.",
        )
        return None
    payload = json.loads(path.read_text())
    bins = payload.get("bins") if isinstance(payload, dict) else payload
    if not isinstance(bins, list) or not bins:
        raise ValueError("Calibration JSON must contain a non-empty bins list")
    usable = [row for row in bins if row.get("count") and row.get("mean_confidence") is not None]
    if not usable:
        _placeholder(output, "Reliability diagram has no populated bins", "The supplied calibration file has no non-empty bins.")
        return payload
    figure, axis = plt.subplots(figsize=(3.8, 3.4))
    axis.plot([0, 1], [0, 1], color="#666666", linestyle="--", linewidth=0.8, label="perfect calibration")
    axis.plot(
        [float(row["mean_confidence"]) for row in usable],
        [float(row["accuracy"]) for row in usable],
        marker="o",
        color="#0072B2",
        linewidth=1.2,
        label="observed",
    )
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.set_xlabel("Mean predicted probability")
    axis.set_ylabel("Observed change frequency")
    title = "Reliability (held-out TRAIN only)"
    if isinstance(payload, dict) and payload.get("ece") is not None:
        title += f", ECE={float(payload['ece']):.3f}"
    axis.set_title(title, fontsize=8)
    axis.legend(frameon=False, fontsize=6)
    _style_axes(axis)
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)
    return payload


def _escape_latex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in str(value))


def write_tables(rows: list[dict], out_dir: Path, ablation_payload: dict | None) -> list[Path]:
    grouped = _rows_by_method(rows)
    pooled_lines = [
        r"% Generated by scripts/make_paper_figures.py from the saved v2 JSON. Do not edit by hand.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Pooled results on the official OSCD test split (v2). True change is 5.17\% of pooled pixels. Otsu's reported score is overall accuracy (OA); its F1 is shown for completeness only.}",
        r"\label{tab:pooled}",
        r"\small",
        r"\begin{tabular}{lrrrrrrl}",
        r"\toprule",
        r"Method & True (\%) & Pred. (\%) & Precision & Recall & F1 & OA & Reported \\",
        r"\midrule",
    ]
    for method in METHOD_ORDER:
        metrics = pooled_metrics(grouped[method])
        pooled_lines.append(
            f"{METHOD_LABELS[method]} & {metrics['true_fraction'] * 100:.2f} & "
            f"{metrics['predicted_fraction'] * 100:.2f} & {metrics['precision']:.4f} & "
            f"{metrics['recall']:.4f} & {metrics['f1']:.4f} & {metrics['overall_accuracy']:.4f} & "
            f"{REPORTED_SCORE[method]} \\\\"
        )
    pooled_lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    pooled_path = out_dir / "generated_results_table.tex"
    pooled_path.write_text("\n".join(pooled_lines))

    per_city_lines = [
        r"% Generated by scripts/make_paper_figures.py from the saved v2 JSON. Do not edit by hand.",
        r"\begin{longtable}{llrrrrrr}",
        r"\caption{Per-city results on the official OSCD test split (v2). Fractions are percentages. Otsu's reported score is OA; its F1 is included for completeness.}\\",
        r"\toprule",
        r"City & Method & True (\%) & Pred. (\%) & Precision & Recall & F1 & OA \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"City & Method & True (\%) & Pred. (\%) & Precision & Recall & F1 & OA \\",
        r"\midrule",
        r"\endhead",
    ]
    for city in sorted({row["city"] for row in rows}):
        for method in METHOD_ORDER:
            row = next(item for item in grouped[method] if item["city"] == city)
            per_city_lines.append(
                f"{_escape_latex(city)} & {METHOD_LABELS[method]} & {_metric(row, 'true_fraction') * 100:.2f} & "
                f"{_metric(row, 'predicted_fraction') * 100:.2f} & {_metric(row, 'precision'):.4f} & "
                f"{_metric(row, 'recall'):.4f} & {_metric(row, 'f1'):.4f} & {_metric(row, 'overall_accuracy'):.4f} \\\\"
            )
    per_city_lines += [r"\bottomrule", r"\end{longtable}", ""]
    per_city_path = out_dir / "generated_per_city_table.tex"
    per_city_path.write_text("\n".join(per_city_lines))

    ablation_lines = [
        r"% Generated by scripts/make_paper_figures.py from an optional auto-improve log.",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Validation-only component ablation on held-out OSCD training cities. Positive $\Delta$F1 means the component helped. This is not a test-set result.}",
        r"\label{tab:ablation}",
        r"\small",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Component & Pairs & Mean $\Delta$F1 & SD & Decision \\",
        r"\midrule",
    ]
    ablation_rows = (ablation_payload or {}).get("ablations", [])
    if ablation_rows:
        for row in ablation_rows:
            mean = "--" if row.get("mean_delta_f1") is None else f"{float(row['mean_delta_f1']):.4f}"
            std = "--" if row.get("std_delta_f1") is None else f"{float(row['std_delta_f1']):.4f}"
            pairs = f"{row.get('pairs_available', 0)}/{row.get('pairs_expected', 0)}"
            ablation_lines.append(
                f"{_escape_latex(row.get('component', 'unknown'))} & {pairs} & {mean} & {std} & "
                f"{_escape_latex(row.get('decision', 'unknown'))} \\\\"
            )
    else:
        ablation_lines.append(
            r"\multicolumn{5}{c}{No auto-improve log was present in this checkout; the ablation was not run.} \\"
        )
    ablation_lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    ablation_path = out_dir / "generated_ablation_table.tex"
    ablation_path.write_text("\n".join(ablation_lines))

    return [pooled_path, per_city_path, ablation_path]


def make_all_figures(
    results_path: Path,
    out_dir: Path,
    *,
    ablation_log: Path | None = None,
    calibration_path: Path | None = None,
) -> dict:
    rows = load_results(results_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "per_city_f1": out_dir / "fig_per_city_f1.png",
        "predicted_vs_true": out_dir / "fig_predicted_vs_true.png",
        "precision_recall": out_dir / "fig_precision_recall.png",
        "ablation": out_dir / "fig_ablation.png",
        "reliability": out_dir / "fig_reliability.png",
        "qualitative": out_dir / "fig_qualitative_placeholder.png",
    }
    plot_per_city_f1(rows, outputs["per_city_f1"])
    plot_predicted_vs_true(rows, outputs["predicted_vs_true"])
    plot_precision_recall(rows, outputs["precision_recall"])
    ablation_payload = plot_ablation(ablation_log, outputs["ablation"])
    plot_reliability(calibration_path, outputs["reliability"])
    _placeholder(
        outputs["qualitative"],
        "Qualitative panel intentionally absent",
        "No redistributable before/after screenshot with verified labels is committed.\n"
        "The UI screenshots in docs/screenshots use mocked API data and are not results.",
    )
    tables = write_tables(rows, out_dir, ablation_payload)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results_file": str(results_path),
        "results_sha256": sha256_file(results_path),
        "rows": len(rows),
        "cities": sorted({row["city"] for row in rows}),
        "methods": list(METHOD_ORDER),
        "figures": {name: path.name for name, path in outputs.items()},
        "tables": [path.name for path in tables],
        "optional_inputs": {
            "ablation_log": None if ablation_log is None or not ablation_log.is_file() else {
                "path": str(ablation_log),
                "sha256": sha256_file(ablation_log),
                "available": True,
            },
            "calibration": None if calibration_path is None or not calibration_path.is_file() else {
                "path": str(calibration_path),
                "sha256": sha256_file(calibration_path),
                "available": True,
            },
        },
    }
    (out_dir / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("benchmarks/results/oscd_results_v2.json"))
    parser.add_argument("--out", type=Path, default=Path("docs/paper/figures"))
    parser.add_argument("--ablation-log", type=Path, default=Path("benchmarks/results/auto_improve_log.json"))
    parser.add_argument("--calibration", type=Path, default=Path("benchmarks/results/uncertainty_holdout.json"))
    args = parser.parse_args(argv)
    manifest = make_all_figures(
        args.results,
        args.out,
        ablation_log=args.ablation_log if args.ablation_log.is_file() else None,
        calibration_path=args.calibration if args.calibration.is_file() else None,
    )
    print(
        f"Wrote {len(manifest['figures'])} figures and {len(manifest['tables'])} tables "
        f"from {manifest['rows']} rows ({manifest['results_sha256'][:12]}) to {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
