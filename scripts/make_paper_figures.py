"""Generate the submission paper's figures and tables from saved data only.

Inputs are ``benchmarks/results/oscd_results_v2.json`` and
``degradation_results.csv``. No network access, model inference, test scoring
or invented values. If the degradation CSV is absent, the resolution figure and
table are replaced by clearly labelled placeholders rather than estimates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.oscd_eval import OFFICIAL_TEST_CITIES  # noqa: E402
from benchmarks.oscd_evidence import (  # noqa: E402
    METHODS,
    baseline_summary,
    bootstrap_summary,
    load_results,
    pooled as pooled_from_rows,
)

METHOD_ORDER = tuple(METHODS)
METHOD_LABELS = {
    "hardcoded": "Hardcoded NDVI/NDBI",
    "percentile": "Percentile 99.0",
    "otsu": "Otsu",
    "cnn_joint": "CNN joint percentile",
    "cnn_reflectance": "CNN reflectance",
}
METHOD_STYLE = {
    "hardcoded": {"color": "#111111", "marker": "o", "linestyle": "-", "mfc": "#111111", "mew": 0.0},
    "percentile": {"color": "#333333", "marker": "s", "linestyle": "--", "mfc": "#333333", "mew": 0.0},
    "otsu": {"color": "#555555", "marker": "^", "linestyle": ":", "mfc": "white", "mew": 0.7},
    "cnn_joint": {"color": "#777777", "marker": "D", "linestyle": "-.", "mfc": "white", "mew": 0.7},
    "cnn_reflectance": {"color": "#999999", "marker": "x", "linestyle": "", "mfc": "none", "mew": 0.8},
}
DEGRADATION_FACTORS = (1, 2, 4, 8, 16, 20)
DEGRADATION_COLUMNS = ("image", "factor", "real_world_resolution", "tp", "fp", "fn")
RESOLUTION_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*$", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _score_metrics(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
    }


def load_degradation_csv(path: Path) -> dict:
    """Pool the saved per-image TP/FP/FN counts at each degradation factor."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing degradation CSV: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in DEGRADATION_COLUMNS if name not in (reader.fieldnames or ())]
        if missing:
            raise ValueError(f"{path} is missing columns: {missing}")
        raw = list(reader)
    if not raw:
        raise ValueError(f"{path} contains no rows")
    counts_by_factor: dict[int, dict[str, dict[str, int]]] = defaultdict(dict)
    resolution_by_factor: dict[int, float] = {}
    for index, row in enumerate(raw, start=2):
        try:
            factor = int(row["factor"])
            counts = {name: int(row[name]) for name in ("tp", "fp", "fn")}
            resolution = float(RESOLUTION_RE.match(row["real_world_resolution"]).group(1))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"{path} row {index} has an invalid factor, resolution or count") from exc
        if any(value < 0 for value in counts.values()):
            raise ValueError(f"{path} row {index} has a negative count")
        if factor in resolution_by_factor and resolution_by_factor[factor] != resolution:
            raise ValueError(f"{path}: factor {factor} has conflicting resolutions")
        resolution_by_factor[factor] = resolution
        image = row["image"].strip()
        if not image:
            raise ValueError(f"{path} row {index} has an empty image name")
        if image in counts_by_factor[factor]:
            raise ValueError(f"{path}: duplicate image/factor {image}/{factor}")
        counts_by_factor[factor][image] = counts
    factors = tuple(sorted(counts_by_factor))
    if factors != DEGRADATION_FACTORS:
        raise ValueError(f"{path}: expected factors {DEGRADATION_FACTORS}, got {factors}")
    image_sets = {factor: set(rows) for factor, rows in counts_by_factor.items()}
    reference = image_sets[factors[0]]
    for factor, images in image_sets.items():
        if images != reference:
            raise ValueError(f"{path}: factor {factor} does not cover the same images as factor {factors[0]}")
    metrics = {}
    for factor in factors:
        totals = {name: sum(row[name] for row in counts_by_factor[factor].values()) for name in ("tp", "fp", "fn")}
        metrics[factor] = {
            **totals,
            **_score_metrics(totals["tp"], totals["fp"], totals["fn"]),
            "n_images": len(counts_by_factor[factor]),
            "predicted_pixels": totals["tp"] + totals["fp"],
        }
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "n_images": len(reference),
        "factors": factors,
        "resolutions": {factor: resolution_by_factor[factor] for factor in factors},
        "metrics": metrics,
    }


def city_f1_interval(counts: dict[str, int], *, seed: int = 0, resamples: int = 10_000, key: str = "") -> list[float]:
    """Pixel-bootstrap interval for one city under an independent-pixel model.

    Saved counts are resampled as a multinomial over TP/FP/FN/TN. This interval
    ignores spatial correlation and is therefore descriptive only.
    """
    total = sum(int(counts[name]) for name in ("tp", "fp", "fn", "tn"))
    if total <= 0 or resamples <= 0:
        return [0.0, 0.0]
    probabilities = np.array([counts[name] for name in ("tp", "fp", "fn", "tn")], dtype=float) / total
    if probabilities.sum() <= 0:
        return [0.0, 0.0]
    probabilities /= probabilities.sum()
    stream = (int(seed) + zlib.crc32(key.encode("utf-8"))) % (2**32)
    samples = np.random.default_rng(stream).multinomial(int(total), probabilities, size=int(resamples))
    tp, fp, fn = samples[:, 0], samples[:, 1], samples[:, 2]
    precision = np.divide(tp, tp + fp, out=np.zeros(len(tp), dtype=float), where=(tp + fp) > 0)
    recall = np.divide(tp, tp + fn, out=np.zeros(len(tp), dtype=float), where=(tp + fn) > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(len(tp), dtype=float), where=(precision + recall) > 0)
    low, high = np.percentile(f1, (2.5, 97.5))
    return [float(low), float(high)]


def city_f1_intervals(by_method: dict[str, dict[str, dict]], *, seed: int = 0, resamples: int = 10_000) -> dict[str, dict[str, dict]]:
    intervals = {}
    for method in METHOD_ORDER:
        intervals[method] = {}
        for city, row in sorted(by_method[method].items()):
            point = float(row["metrics"]["f1"])
            low, high = city_f1_interval(row["metrics"], seed=seed, resamples=resamples, key=f"{method}:{city}")
            intervals[method][city] = {"point": point, "ci95": [low, high]}
    return intervals


def _placeholder(output: Path, title: str, message: str) -> None:
    figure, axis = plt.subplots(figsize=(3.5, 2.5))
    axis.axis("off")
    axis.text(0.5, 0.62, title, ha="center", va="center", fontsize=9, weight="bold")
    axis.text(0.5, 0.36, message, ha="center", va="center", fontsize=7, wrap=True)
    figure.tight_layout(pad=0.3)
    figure.savefig(output, dpi=300)
    plt.close(figure)


def plot_resolution_f1(data: dict | None, output: Path) -> bool:
    if data is None:
        _placeholder(
            output,
            "F1-versus-resolution data not found",
            "No degradation_results.csv was supplied.\nNo F1 values are inferred.",
        )
        return False
    factors = data["factors"]
    positions = np.arange(len(factors))
    metrics = data["metrics"]
    figure, axis = plt.subplots(figsize=(3.5, 2.55))
    axis.plot(
        positions,
        [100 * metrics[factor]["f1"] for factor in factors],
        color="#111111",
        marker="o",
        markersize=3.8,
        linewidth=1.2,
        label="F1",
    )
    axis.plot(
        positions,
        [100 * metrics[factor]["precision"] for factor in factors],
        color="#555555",
        marker="s",
        markersize=3.2,
        linewidth=0.9,
        linestyle="--",
        label="Precision",
    )
    axis.plot(
        positions,
        [100 * metrics[factor]["recall"] for factor in factors],
        color="#888888",
        marker="^",
        markersize=3.4,
        linewidth=0.9,
        linestyle=":",
        label="Recall",
    )
    for position, factor in zip(positions, factors):
        axis.annotate(
            f"{100 * metrics[factor]['f1']:.1f}",
            (position, 100 * metrics[factor]["f1"]),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=5.8,
            color="#111111",
        )
    axis.set_xticks(positions, [f"{data['resolutions'][factor]:g}" for factor in factors])
    axis.set_xlabel("Simulated resolution (m)", fontsize=7.5)
    axis.set_ylabel("Score (%)", fontsize=7.5)
    axis.set_ylim(-3, 106)
    axis.tick_params(labelsize=7)
    axis.grid(axis="y", color="#dddddd", linewidth=0.5)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, fontsize=6.3, loc="center right")
    figure.tight_layout(pad=0.35)
    figure.savefig(output, dpi=300)
    plt.close(figure)
    return True


def plot_oscd_panel(by_method: dict[str, dict[str, dict]], intervals: dict, output: Path) -> None:
    cities = sorted({city for rows in by_method.values() for city in rows})
    positions = np.arange(len(cities), dtype=float)
    figure, (left, right) = plt.subplots(
        1,
        2,
        figsize=(7.16, 2.95),
        gridspec_kw={"width_ratios": [1.28, 1.0]},
    )

    offsets = {method: (index - (len(METHOD_ORDER) - 1) / 2) * 0.13 for index, method in enumerate(METHOD_ORDER)}
    for method in METHOD_ORDER:
        style = METHOD_STYLE[method]
        points = np.array([intervals[method][city]["point"] for city in cities])
        lows = np.array([intervals[method][city]["ci95"][0] for city in cities])
        highs = np.array([intervals[method][city]["ci95"][1] for city in cities])
        left.errorbar(
            positions + offsets[method],
            points,
            yerr=np.vstack((np.maximum(points - lows, 0), np.maximum(highs - points, 0))),
            fmt=style["marker"],
            color=style["color"],
            markerfacecolor=style["mfc"],
            markeredgewidth=style["mew"],
            markersize=3.3,
            capsize=1.2,
            elinewidth=0.5,
            linestyle="none",
            label=METHOD_LABELS[method],
            zorder=3,
        )
    random_expected = [
        baseline_summary(by_method["hardcoded"][city]["metrics"])["random_at_prevalence"]["f1"] for city in cities
    ]
    left.scatter(
        positions,
        random_expected,
        marker="_",
        s=22,
        color="#555555",
        linewidths=0.8,
        label="Random at prevalence",
        zorder=2,
    )
    top = max(
        [intervals[method][city]["ci95"][1] for method in METHOD_ORDER for city in cities]
        + [max(random_expected)]
        + [0.05]
    )
    left.set_xticks(positions, cities, rotation=35, ha="right", fontsize=6.2)
    left.set_ylabel("F1", fontsize=7.5)
    left.set_ylim(0, top * 1.18)
    left.tick_params(axis="y", labelsize=7)
    left.grid(axis="y", color="#dddddd", linewidth=0.5)
    left.spines[["top", "right"]].set_visible(False)
    left.set_title("(a) Per-city F1, 95% pixel intervals", fontsize=7.8)
    handles = [
        Line2D([], [], color=METHOD_STYLE[method]["color"], marker=METHOD_STYLE[method]["marker"],
               linestyle="none", markersize=3.5, markerfacecolor=METHOD_STYLE[method]["mfc"],
               markeredgewidth=METHOD_STYLE[method]["mew"], label=METHOD_LABELS[method])
        for method in METHOD_ORDER
    ]
    handles.append(Line2D([], [], color="#555555", marker="_", linestyle="none", markersize=6, label="Random at prevalence"))
    left.legend(handles=handles, frameon=False, fontsize=5.4, ncol=2, loc="upper left")

    for method in METHOD_ORDER:
        style = METHOD_STYLE[method]
        true = [100 * float(by_method[method][city]["metrics"]["true_fraction"]) for city in cities]
        predicted = [100 * float(by_method[method][city]["metrics"]["predicted_fraction"]) for city in cities]
        right.scatter(
            true,
            predicted,
            marker=style["marker"],
            s=15,
            color=style["color"],
            facecolors=style["mfc"],
            linewidths=style["mew"],
            label=METHOD_LABELS[method],
            zorder=3,
        )
    right.plot([0, 11], [0, 11], color="#555555", linewidth=0.7, linestyle="--", zorder=1)
    right.set_yscale("symlog", linthresh=0.01, linscale=0.35)
    right.set_xlim(0, 11)
    right.set_ylim(0, 120)
    right.set_xticks([0, 2, 4, 6, 8, 10])
    right.set_yticks([0, 0.01, 0.1, 1, 10, 100])
    right.set_yticklabels(["0", "0.01", "0.1", "1", "10", "100"])
    right.set_xlabel("True change (%)", fontsize=7.5)
    right.set_ylabel("Predicted change (%)", fontsize=7.5)
    right.tick_params(labelsize=7)
    right.grid(axis="y", color="#dddddd", linewidth=0.5)
    right.spines[["top", "right"]].set_visible(False)
    right.set_title("(b) Predicted and true change", fontsize=7.8)
    right.legend(frameon=False, fontsize=5.4, loc="lower right")

    figure.tight_layout(pad=0.35, w_pad=1.0)
    figure.savefig(output, dpi=300)
    plt.close(figure)


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


def write_degradation_table(data: dict | None, out_dir: Path) -> Path:
    path = out_dir / "generated_degradation_table.tex"
    if data is None:
        caption = "CNN scores versus simulated resolution. Source data not found; table not generated."
    else:
        caption = (
            f"CNN scores versus simulated resolution on the {data['n_images']:,} LEVIR-CD test pairs. "
            "Values are computed from pooled TP/FP/FN counts, not averaged per image."
        )
    lines = [
        r"% Generated by scripts/make_paper_figures.py from degradation_results.csv. Do not edit by hand.",
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{{caption}}}",
        r"\label{tab:degradation}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{rrrrrr}",
        r"\toprule",
        r"Factor & Resolution (m) & Precision & Recall & F1 & IoU \\",
        r"\midrule",
    ]
    if data is None:
        lines.append(r"\multicolumn{6}{c}{Source data not found; table not generated.} \\")
    else:
        for factor in data["factors"]:
            metrics = data["metrics"][factor]
            lines.append(
                f"{factor} & {data['resolutions'][factor]:g} & {100 * metrics['precision']:.2f} & "
                f"{100 * metrics['recall']:.2f} & {100 * metrics['f1']:.2f} & {100 * metrics['iou']:.2f} \\\\"
            )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    path.write_text("\n".join(lines))
    return path


def write_oscd_table(by_method: dict[str, dict[str, dict]], bootstrap: dict, out_dir: Path) -> Path:
    path = out_dir / "generated_oscd_table.tex"
    hardcoded = pooled_from_rows(by_method["hardcoded"])
    true_fraction = hardcoded["true_fraction"]
    otsu_fraction = pooled_from_rows(by_method["otsu"])["predicted_fraction"]
    total_pixels = hardcoded["tp"] + hardcoded["fp"] + hardcoded["fn"] + hardcoded["tn"]
    lines = [
        r"% Generated by scripts/make_paper_figures.py from benchmarks/results/oscd_results_v2.json. Do not edit by hand.",
        r"\begin{table*}[t]",
        r"\centering",
        rf"\caption{{Pooled results on the ten official OSCD test cities ({total_pixels:,} pixels; true change {100 * true_fraction:.2f}\%). "
        r"F1 intervals are 95\% percentile intervals from a city-level bootstrap (seed 0, 10,000 resamples); they reflect city sampling only. "
        r"OA is shown for every method; Otsu's predicted fraction is "
        rf"{100 * otsu_fraction:.2f}\%, so its OA is its headline score. "
        r"Precision is reported as 0 by convention for methods with no positive predictions.}",
        r"\label{tab:oscd}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{lrrrrrrr}",
        r"\toprule",
        r"Method & Pred. (\%) & Precision & Recall & F1 & F1 95\% CI & IoU & OA \\",
        r"\midrule",
    ]
    for method in METHOD_ORDER:
        metrics = pooled_from_rows(by_method[method])
        estimate = bootstrap["methods"][method]["f1"]["ci95"]
        lines.append(
            f"{METHOD_LABELS[method]} & {100 * metrics['predicted_fraction']:.2f} & "
            f"{metrics['precision']:.4f} & {metrics['recall']:.4f} & {metrics['f1']:.4f} & "
            f"[{estimate[0]:.4f}, {estimate[1]:.4f}] & {metrics['iou']:.4f} & {metrics['overall_accuracy']:.4f} \\\\"
        )
    random = baseline_summary(pooled_from_rows(by_method["hardcoded"]))["random_at_prevalence"]
    no_change = baseline_summary(pooled_from_rows(by_method["hardcoded"]))["all_no_change"]
    lines.append(
        f"Random at prevalence & {100 * true_fraction:.2f} & {random['precision']:.4f} & {random['recall']:.4f} & "
        f"{random['f1']:.4f} & -- & {random['iou']:.4f} & -- \\\\"
    )
    lines.append(
        f"All no change & 0.00 & -- & {no_change['recall']:.4f} & {no_change['f1']:.4f} & -- & {no_change['iou']:.4f} & "
        f"{no_change['overall_accuracy']:.4f} \\\\"
    )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    path.write_text("\n".join(lines))
    return path


def make_all_figures(
    results_path: Path,
    out_dir: Path,
    *,
    degradation_csv: Path | None = None,
    seed: int = 0,
    resamples: int = 10_000,
) -> dict:
    by_method = load_results(results_path, expected_cities=OFFICIAL_TEST_CITIES)
    out_dir.mkdir(parents=True, exist_ok=True)
    degradation = None
    degradation_error = None
    if degradation_csv is not None:
        try:
            degradation = load_degradation_csv(Path(degradation_csv))
        except FileNotFoundError as exc:
            degradation_error = str(exc)
    if degradation is None:
        resolution_name = "fig_f1_vs_resolution_placeholder.png"
        plot_resolution_f1(None, out_dir / resolution_name)
    else:
        resolution_name = "fig_f1_vs_resolution.png"
        plot_resolution_f1(degradation, out_dir / resolution_name)
    intervals = city_f1_intervals(by_method, seed=seed, resamples=resamples)
    panel_name = "fig_oscd_per_city_and_fractions.png"
    plot_oscd_panel(by_method, intervals, out_dir / panel_name)
    bootstrap = bootstrap_summary(by_method, seed=seed, resamples=resamples)
    degradation_table = write_degradation_table(degradation, out_dir)
    oscd_table = write_oscd_table(by_method, bootstrap, out_dir)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results_file": str(results_path),
        "results_sha256": sha256_file(results_path),
        "rows": sum(len(rows) for rows in by_method.values()),
        "cities": sorted({city for rows in by_method.values() for city in rows}),
        "methods": list(METHOD_ORDER),
        "figures": {
            "resolution_f1": resolution_name,
            "oscd_per_city_and_fractions": panel_name,
        },
        "tables": [degradation_table.name, oscd_table.name],
        "degradation": {
            "available": degradation is not None,
            "error": degradation_error,
            "path": None if degradation is None else degradation["path"],
            "sha256": None if degradation is None else degradation["sha256"],
            "n_images": None if degradation is None else degradation["n_images"],
            "factors": None if degradation is None else list(degradation["factors"]),
            "resolutions_m": None if degradation is None else [degradation["resolutions"][f] for f in degradation["factors"]],
        },
        "intervals": {
            "pooled": "city bootstrap percentile 2.5-97.5",
            "pooled_seed": seed,
            "pooled_resamples": resamples,
            "per_city": "pixel bootstrap percentile 2.5-97.5, independent-pixel approximation; spatial correlation not modeled",
            "per_city_seed": seed,
            "per_city_resamples": resamples,
        },
    }
    (out_dir / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("benchmarks/results/oscd_results_v2.json"))
    parser.add_argument("--degradation", type=Path, default=Path("degradation_results.csv"))
    parser.add_argument("--out", type=Path, default=Path("docs/paper/figures"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resamples", type=int, default=10_000)
    args = parser.parse_args(argv)
    manifest = make_all_figures(
        args.results,
        args.out,
        degradation_csv=args.degradation,
        seed=args.seed,
        resamples=args.resamples,
    )
    print(
        f"Wrote {len(manifest['figures'])} figures and {len(manifest['tables'])} tables "
        f"from {manifest['rows']} OSCD rows ({manifest['results_sha256'][:12]}) to {args.out}"
    )
    print(f"degradation_available={manifest['degradation']['available']} images={manifest['degradation']['n_images']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
