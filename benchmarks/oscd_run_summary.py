"""Build a factual Markdown run summary from checkpointed OSCD results."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def _aggregate(rows: list[dict]) -> dict[str, float | int]:
    counts = {key: sum(int(row["metrics"][key]) for row in rows) for key in ("tp", "fp", "fn", "tn")}
    tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "predicted_fraction": (tp + fp) / total if total else 0.0,
        "true_fraction": (tp + fn) / total if total else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
        "overall_accuracy": (tp + tn) / total if total else 0.0,
    }


def render_run_summary(payload: list[dict]) -> str:
    metadata_rows = [row for row in payload if row.get("record_type") == "run_metadata"]
    if len(metadata_rows) != 1:
        raise ValueError(f"Expected exactly one run_metadata record, found {len(metadata_rows)}")
    metadata = metadata_rows[0].get("metadata", {})
    required = (
        "run_date", "code_commit", "selected_spectral_configs_line",
        "cnn_preprocessing_selected_line", "pytest_summary_line",
    )
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise ValueError(f"Run metadata is missing required fields: {', '.join(missing)}")
    if not isinstance(metadata.get("grid_edge_warnings"), list):
        raise ValueError("Run metadata must include grid_edge_warnings as a list")

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in payload:
        if row.get("record_type") == "run_metadata" or row.get("split") != "test" or "metrics" not in row:
            continue
        grouped[(row["pipeline"], row["configuration"])].append(row)

    lines = [
        "# OSCD benchmark run summary",
        "",
        f"- Run date: {metadata['run_date']}",
        f"- Code commit: `{metadata['code_commit']}`",
        "",
        metadata["selected_spectral_configs_line"],
        "",
        "Grid-edge warnings:",
    ]
    warnings = metadata["grid_edge_warnings"]
    lines.extend(f"- {warning}" for warning in warnings) if warnings else lines.append("- None recorded.")
    lines.extend(("", metadata["cnn_preprocessing_selected_line"], "", f"Pytest: {metadata['pytest_summary_line']}", ""))
    lines.extend((
        "## Aggregate test results",
        "",
        "| Pipeline | Configuration | Predicted fraction | True fraction | Precision | Recall | F1 | IoU | OA |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ))
    for (pipeline, configuration), rows in sorted(grouped.items()):
        value = _aggregate(rows)
        lines.append(
            f"| {pipeline} | {configuration} | {value['predicted_fraction']:.4f} | "
            f"{value['true_fraction']:.4f} | {value['precision']:.4f} | {value['recall']:.4f} | "
            f"{value['f1']:.4f} | {value['iou']:.4f} | {value['overall_accuracy']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def write_run_summary(results_path: Path, summary_path: Path) -> str:
    """Read saved results JSON and write its reproducible run summary."""
    payload = json.loads(results_path.read_text())
    summary = render_run_summary(payload)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary)
    return summary
