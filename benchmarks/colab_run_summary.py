"""Render the Colab hand-off summary from saved run artifacts.

The summary is descriptive: it reports a training-city robustness check and a
model load check. It never scores an official OSCD test city.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def render_colab_summary(
    *,
    loco_path: Path,
    model_check_path: Path,
    pytest_summary_path: Path,
    commit: str,
    pytest_exit_code: int,
    generated_date: str | None = None,
) -> str:
    loco_path = Path(loco_path)
    model_check_path = Path(model_check_path)
    pytest_summary_path = Path(pytest_summary_path)
    loco = json.loads(loco_path.read_text())
    model = json.loads(model_check_path.read_text())
    pytest_line = pytest_summary_path.read_text().strip()

    _require(loco.get("result_status") == "computed_on_training_cities_only", "LOCO report is not marked training-only")
    guards = loco.get("guards", {})
    _require(guards.get("official_test_cities_in_train_list") == [], "LOCO report lists an official test city in train.txt")
    _require(guards.get("test_labels_path_accepted") is False, "LOCO report does not record the test-label guard")
    _require(bool(re.fullmatch(r"[0-9a-f]{40}", commit)), "Commit must be a full 40-character SHA-1")
    _require(isinstance(pytest_exit_code, int), "Pytest exit code must be an integer")
    _require(bool(pytest_line), "Pytest summary is empty")
    _require(isinstance(model.get("size_bytes"), int) and model["size_bytes"] > 0, "Model size is missing")
    _require(bool(re.fullmatch(r"[0-9a-f]{64}", model.get("sha256", ""))), "Model SHA-256 is missing")
    _require(isinstance(model.get("loads"), bool), "Model load status is missing")

    families = loco.get("families", {})
    _require(bool(families), "LOCO report has no families")
    date_text = generated_date or date.today().isoformat()
    protocol = loco.get("protocol", {})
    lines = [
        "# Colab run summary",
        "",
        f"- Generated: {date_text}",
        f"- Code commit: `{commit}`",
        f"- Pytest: `{pytest_line}` (exit code {pytest_exit_code})",
        "- Scope: training-city robustness and a model load check only.",
        "",
        "**No official OSCD test city was scored, no training or fine-tuning was run, and v3 was not run.**",
        "",
        "## Training-city leave-one-city-out robustness",
        "",
        f"Source: `benchmarks/results/oscd_loco_thresholds.json` (SHA-256 `{_sha256(loco_path)}`).",
        "",
        f"Selection: {protocol.get('selection', 'not recorded')}",
        f"Evaluation: {protocol.get('evaluation', 'not recorded')}",
        "",
        "| Family | Pooled held-out F1 | IoU | Precision | Recall | Distinct selected configs | Grid-edge folds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for family, values in families.items():
        pooled = values["pooled_held_out"]
        lines.append(
            f"| {family} | {pooled['f1']:.4f} | {pooled['iou']:.4f} | "
            f"{pooled['precision']:.4f} | {pooled['recall']:.4f} | "
            f"{values['distinct_selected_configs']} | {values['folds_with_grid_edge_warning']} |"
        )
    lines.extend(("", "Full-train selections (in-sample, not test results):", ""))
    for family, values in families.items():
        selected = values["full_train_selection"]
        lines.append(
            f"- {family}: `{json.dumps(selected['config'], sort_keys=True)}`; "
            f"in-sample pooled F1 {selected['pooled_f1_on_train_cities_in_sample']:.4f}; "
            f"grid-edge warning: {selected['grid_edge_warning']}"
        )
    lines.extend(("", "**This is a training-split robustness check, not a test-set score.**", ""))
    caveats = loco.get("caveats", [])
    if caveats:
        lines.append("Caveats:")
        lines.extend(f"- {caveat}" for caveat in caveats)
        lines.append("")

    lines.extend(
        (
            "## Model check",
            "",
            f"Source: `benchmarks/results/colab_model_check.json` (SHA-256 `{_sha256(model_check_path)}`).",
            "",
            f"- File: `{model.get('path', 'model.onnx')}`",
            f"- Size: {model['size_bytes']:,} bytes (expected {model.get('expected_bytes', 'not recorded'):,})"
            if isinstance(model.get("expected_bytes"), int)
            else f"- Size: {model['size_bytes']:,} bytes (expected size not recorded)",
            f"- SHA-256: `{model['sha256']}`",
            f"- onnxruntime load: {'yes' if model['loads'] else 'no'}",
        )
    )
    inputs = model.get("input_names") or []
    providers = model.get("providers") or []
    lines.append(f"- Inputs: {', '.join(f'`{name}`' for name in inputs) if inputs else 'not available'}")
    lines.append(f"- Providers: {', '.join(providers) if providers else 'not available'}")
    if model.get("error"):
        lines.append(f"- Error: {model['error']}")
    lines.extend(
        (
            "",
            "## Not run",
            "",
            "- Official OSCD test-city scoring; no test label was read.",
            "- Training, fine-tuning or seed variation.",
            "- The preregistered v3 scoring event.",
            "- Any accuracy or validation claim beyond the saved v2 results.",
            "",
        )
    )
    return "\n".join(lines)


def write_colab_summary(
    *,
    loco_path: Path,
    model_check_path: Path,
    pytest_summary_path: Path,
    commit: str,
    pytest_exit_code: int,
    output_path: Path,
    generated_date: str | None = None,
) -> str:
    summary = render_colab_summary(
        loco_path=loco_path,
        model_check_path=model_check_path,
        pytest_summary_path=pytest_summary_path,
        commit=commit,
        pytest_exit_code=pytest_exit_code,
        generated_date=generated_date,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary)
    return summary
