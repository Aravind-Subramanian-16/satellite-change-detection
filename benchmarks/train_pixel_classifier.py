#!/usr/bin/env python3
"""Train the optional OSCD per-pixel change classifier on TRAIN cities only.

The official ten-city test split is never loaded, featurised or scored here.
Three seeded held-out TRAIN cities select the probability threshold; the other
eleven cities fit the model. The joblib artifact is written outside git.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import oscd_eval
from learned_features import BAND_KEYS, OFFICIAL_TEST_CITIES, assert_no_test_cities, build_pixel_features
from provenance import get_commit_hash

HELD_OUT_CITIES = 3
THRESHOLD_GRID = tuple(round(value, 2) for value in np.linspace(0.05, 0.95, 19))
DEFAULT_SEED = 42


def load_city_bands(images_root: Path, train_labels_root: Path, city: str) -> tuple[dict, dict, np.ndarray]:
    mask, label_shape = oscd_eval.load_label(train_labels_root, city)
    acquisitions: dict[str, dict] = {"before": {}, "after": {}}
    for time, directory_name in (("before", "imgs_1_rect"), ("after", "imgs_2_rect")):
        directory = images_root / city / directory_name
        for band in BAND_KEYS:
            path = oscd_eval.band_path(directory, band)
            array = oscd_eval.raster(path)
            if array.shape != label_shape:
                raise ValueError(
                    f"{city}: {time} {band} shape {array.shape} != label shape {label_shape}"
                )
            acquisitions[time][band] = array
    return acquisitions["before"], acquisitions["after"], mask


def sample_rows(
    features: np.ndarray,
    mask: np.ndarray,
    max_pixels: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Flatten and deterministically subsample while preserving class prevalence."""
    flat = features.reshape(-1, features.shape[-1])
    labels = mask.ravel().astype(np.uint8)
    if flat.shape[0] != labels.shape[0]:
        raise ValueError("Feature and label pixel counts differ")
    if max_pixels > 0 and flat.shape[0] > max_pixels:
        rng = np.random.default_rng(seed)
        indices = np.sort(rng.choice(flat.shape[0], size=int(max_pixels), replace=False))
        return flat[indices], labels[indices]
    return flat, labels


def metrics(prediction: np.ndarray, label: np.ndarray) -> dict[str, float | int]:
    return oscd_eval.metrics(prediction, label)


def select_threshold(probabilities: np.ndarray, labels: np.ndarray) -> tuple[float, list[dict]]:
    rows = []
    for threshold in THRESHOLD_GRID:
        scores = metrics(probabilities >= threshold, labels)
        rows.append({"threshold": threshold, **scores})
    best = max(rows, key=lambda row: (row["f1"], row["precision"], -row["threshold"]))
    return float(best["threshold"]), rows


def build_training_data(images_root: Path, labels_root: Path, cities: list[str], max_pixels: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    features, labels = [], []
    for city in cities:
        before, after, mask = load_city_bands(images_root, labels_root, city)
        stack, names = build_pixel_features(before, after)
        x, y = sample_rows(stack, mask, max_pixels, seed)
        features.append(x)
        labels.append(y)
        print(f"  {city}: {x.shape[0]:,} pixels, {int(y.sum()):,} change, {len(names)} features")
    return np.concatenate(features), np.concatenate(labels)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--train-labels-root", type=Path, required=True)
    parser.add_argument("--output-model", type=Path, default=Path("artifacts/learned_pixel_model.joblib"))
    parser.add_argument("--max-pixels-per-city", type=int, default=80_000)
    parser.add_argument("--validation-max-pixels-per-city", type=int, default=150_000)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_split = args.images_root / "train.txt"
    train_cities = oscd_eval.read_city_list(train_split)
    if len(train_cities) != 14:
        raise ValueError(f"Expected 14 OSCD TRAIN cities, found {len(train_cities)} in {train_split}")
    assert_no_test_cities(train_cities)
    rng = np.random.default_rng(args.seed)
    held_out = sorted(rng.choice(sorted(train_cities), size=HELD_OUT_CITIES, replace=False).tolist())
    fit_cities = sorted(set(train_cities) - set(held_out))
    assert_no_test_cities(held_out)
    print(f"Fit cities ({len(fit_cities)}): {', '.join(fit_cities)}")
    print(f"Held-out TRAIN cities ({len(held_out)}): {', '.join(held_out)}")
    print("Official test cities are excluded by guard and are not read.")

    print("Building fit features...")
    x_fit, y_fit = build_training_data(
        args.images_root, args.train_labels_root, fit_cities, args.max_pixels_per_city, args.seed
    )
    print("Building held-out features...")
    x_val, y_val = build_training_data(
        args.images_root,
        args.train_labels_root,
        held_out,
        args.validation_max_pixels_per_city,
        args.seed + 1,
    )

    from sklearn.ensemble import HistGradientBoostingClassifier

    hyperparameters = {
        "max_iter": 200,
        "learning_rate": 0.08,
        "max_leaf_nodes": 31,
        "l2_regularization": 1.0,
        "class_weight": "balanced",
        "random_state": args.seed,
        "early_stopping": False,
    }
    model = HistGradientBoostingClassifier(**hyperparameters)
    print(f"Fitting {type(model).__name__} on {x_fit.shape[0]:,} pixels x {x_fit.shape[1]} features...")
    model.fit(x_fit, y_fit)
    probabilities = model.predict_proba(x_val)[:, 1].astype(np.float32)
    threshold, threshold_rows = select_threshold(probabilities, y_val)
    validation = metrics(probabilities >= threshold, y_val)
    at_half = metrics(probabilities >= 0.5, y_val)
    print(f"Selected validation threshold {threshold:.2f}; F1={validation['f1']:.4f}, precision={validation['precision']:.4f}, recall={validation['recall']:.4f}")

    feature_names = tuple(
        build_pixel_features(
            {key: np.ones((2, 2), dtype=np.float32) for key in BAND_KEYS},
            {key: np.ones((2, 2), dtype=np.float32) for key in BAND_KEYS},
        )[1]
    )
    if len(feature_names) != x_fit.shape[1]:
        raise RuntimeError("Feature-name count does not match the trained matrix")
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_commit": get_commit_hash(),
        "seed": args.seed,
        "fit_cities": fit_cities,
        "held_out_train_cities": held_out,
        "official_test_cities_excluded": list(OFFICIAL_TEST_CITIES),
        "fit_pixels": int(x_fit.shape[0]),
        "held_out_pixels": int(x_val.shape[0]),
        "fit_change_percent": round(float(y_fit.mean() * 100.0), 4),
        "held_out_change_percent": round(float(y_val.mean() * 100.0), 4),
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),
        "hyperparameters": hyperparameters,
        "selected_threshold": threshold,
        "validation_metrics_at_selected_threshold": validation,
        "validation_metrics_at_0_5": at_half,
        "threshold_sweep": threshold_rows,
        "sampling": {
            "fit_max_pixels_per_city": args.max_pixels_per_city,
            "validation_max_pixels_per_city": args.validation_max_pixels_per_city,
        },
        "test_split_scored": False,
    }
    bundle = {
        "model": model,
        "threshold": threshold,
        "feature_names": feature_names,
        "metadata": metadata,
    }
    import joblib

    args.output_model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.output_model)
    summary_path = args.output_model.with_suffix(".metrics.json")
    summary_path.write_text(json.dumps(metadata, indent=2))
    print(f"Wrote {args.output_model} and {summary_path}")
    print("Test-set scoring is intentionally not performed by this script.")


if __name__ == "__main__":
    main()
