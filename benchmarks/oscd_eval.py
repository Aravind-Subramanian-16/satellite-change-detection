#!/usr/bin/env python3
"""Evaluate the application pipelines on the official OSCD directory layout.

Threshold parameters are selected on training cities only. Test-city rows are
checkpointed after every pipeline, so rerunning resumes interrupted Colab work.
"""
from __future__ import annotations

import argparse
import base64
import io
import itertools
import json
import sys
import warnings
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spectral_pipeline import SpectralConfig, detect_from_indices

OFFICIAL_TEST_CITIES = ("brasilia", "montpellier", "norcia", "rio", "saclay_w", "valencia", "dubai", "lasvegas", "milano", "chongqing")
BANDS = ("B02", "B03", "B04", "B08", "B11")
HARDCODED_NDVI_GRID = (-0.30, -0.20, -0.15, -0.10, -0.05)
HARDCODED_NDBI_GRID = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
PERCENTILE_GRID = (80.0, 85.0, 90.0, 95.0, 97.5, 98.0, 99.0, 99.5)
CNN_PREPROCESS_VARIANTS = ("reflectance", "joint_percentile")


def read_city_list(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing split file: {path}")
    return [city.strip() for city in path.read_text().replace("\n", ",").split(",") if city.strip()]


def metrics(prediction: np.ndarray, label: np.ndarray) -> dict[str, float | int]:
    predicted, actual = prediction.astype(bool), label.astype(bool)
    tp = int((predicted & actual).sum()); fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum()); tn = int((~predicted & ~actual).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    total = tp + fp + fn + tn
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0, "overall_accuracy": (tp + tn) / total, "predicted_fraction": (tp + fp) / total, "true_fraction": (tp + fn) / total, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def aggregate(rows: list[dict]) -> dict[str, float | int]:
    counts = {name: sum(row["metrics"][name] for row in rows) for name in ("tp", "fp", "fn", "tn")}
    predicted = np.array([1] * (counts["tp"] + counts["fp"]) + [0] * (counts["fn"] + counts["tn"]))
    label = np.array([1] * counts["tp"] + [0] * counts["fp"] + [1] * counts["fn"] + [0] * counts["tn"])
    return metrics(predicted, label)


def raster(path: Path) -> np.ndarray:
    try:
        import rasterio
        from rasterio.errors import NotGeoreferencedWarning
    except ImportError as exc:
        raise RuntimeError("OSCD evaluation requires rasterio; install requirements.txt") from exc
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(path) as dataset:
            return dataset.read(1).astype(np.float32)


def band_path(directory: Path, band: str) -> Path:
    matches = sorted(path for path in directory.glob(f"{band}*.tif") if path.is_file())
    if len(matches) != 1:
        raise FileNotFoundError(f"{directory}: expected exactly one {band}.tif, found {len(matches)}")
    return matches[0]


def rgb(red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Convert OSCD's scaled Sentinel-2 reflectance to Pipeline A RGB input."""
    return np.clip(np.dstack((red, green, blue)) / 10000.0 * 255.0, 0, 255).astype(np.uint8)


def preprocess_rgb_pair(rgb_a: np.ndarray, rgb_b: np.ndarray, preprocess: str) -> tuple[np.ndarray, np.ndarray]:
    """Scale both acquisitions with reflectance or shared city-wide percentiles."""
    rgb_a, rgb_b = np.asarray(rgb_a), np.asarray(rgb_b)
    if rgb_a.ndim != 3 or rgb_a.shape[-1] != 3 or rgb_b.ndim != 3 or rgb_b.shape[-1] != 3:
        raise ValueError("RGB acquisitions must both have shape HxWx3")
    if preprocess == "reflectance":
        return tuple(np.clip(rgb / 10000.0 * 255.0, 0, 255).astype(np.uint8) for rgb in (rgb_a, rgb_b))
    if preprocess != "joint_percentile":
        raise ValueError(f"Unknown CNN preprocessing variant: {preprocess}")
    combined = np.concatenate((rgb_a.reshape(-1), rgb_b.reshape(-1)))
    low, high = np.percentile(combined, (2, 98))
    if high <= low:
        return np.zeros(rgb_a.shape, dtype=np.uint8), np.zeros(rgb_b.shape, dtype=np.uint8)
    scale = 255.0 / (high - low)
    return tuple(np.clip((rgb - low) * scale, 0, 255).astype(np.uint8) for rgb in (rgb_a, rgb_b))


def load_label(labels_root: Path, city: str) -> tuple[np.ndarray, tuple[int, int]]:
    """Read the ground-truth change mask from the OSCD label GeoTIFF.

    The label file is ``<city>/cm/<city>-cm.tif``, band 1.  Valid pixel
    values are **1** (no change) and **2** (change).  Returns a boolean
    mask where ``True`` means *change*.
    """
    label_path = labels_root / city / "cm" / f"{city}-cm.tif"
    if not label_path.is_file():
        raise FileNotFoundError(f"{city}: missing change label GeoTIFF {label_path}")
    try:
        import rasterio
        from rasterio.errors import NotGeoreferencedWarning
    except ImportError as exc:
        raise RuntimeError("OSCD evaluation requires rasterio; install requirements.txt") from exc
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(label_path) as ds:
            expected_shape = (ds.height, ds.width)
            raw = ds.read(1)
    values = set(np.unique(raw).tolist())
    if not values.issubset({1, 2}):
        raise ValueError(
            f"{city}: label GeoTIFF must contain only values {{1, 2}}, got {sorted(values)}"
        )
    mask = raw == 2
    if mask.shape != expected_shape:
        raise ValueError(
            f"{city}: label mask shape {mask.shape} does not match GeoTIFF band dimensions "
            f"{expected_shape}; refusing to resize"
        )
    return mask, expected_shape


def load_city(images_root: Path, labels_root: Path, city: str) -> dict:
    before_dir, after_dir = images_root / city / "imgs_1_rect", images_root / city / "imgs_2_rect"
    mask, label_shape = load_label(labels_root, city)
    bands, mismatches = {}, []
    for time, directory in (("before", before_dir), ("after", after_dir)):
        for band in BANDS:
            path = band_path(directory, band)
            image = raster(path)
            bands[time, band] = image
            if image.shape != label_shape:
                mismatches.append(f"{time} {band}: band {image.shape}, label {label_shape} ({path})")
    if mismatches:
        raise ValueError(f"{city}: raster/label dimensions differ; refusing to resize:\n" + "\n".join(mismatches))
    def indices(time: str) -> tuple[np.ndarray, np.ndarray]:
        nir, red, swir = bands[time, "B08"], bands[time, "B04"], bands[time, "B11"]
        return (nir - red) / np.maximum(nir + red, 1e-6), (swir - nir) / np.maximum(swir + nir, 1e-6)
    ndvi_a, ndbi_a = indices("before"); ndvi_b, ndbi_b = indices("after")
    raw_rgb_a = np.dstack((bands["before", "B04"], bands["before", "B03"], bands["before", "B02"]))
    raw_rgb_b = np.dstack((bands["after", "B04"], bands["after", "B03"], bands["after", "B02"]))
    return {"city": city, "mask": mask, "ndvi_a": ndvi_a, "ndbi_a": ndbi_a, "ndvi_b": ndvi_b, "ndbi_b": ndbi_b, "rgb_raw_a": raw_rgb_a, "rgb_raw_b": raw_rgb_b}


def spectral_prediction(data: dict, config: SpectralConfig) -> tuple[np.ndarray, dict]:
    prediction, _, thresholds = detect_from_indices(data["ndvi_a"], data["ndbi_a"], data["ndvi_b"], data["ndbi_b"], config=config)
    return prediction, thresholds


def select_configs(training: list[dict]) -> list[tuple[str, SpectralConfig]]:
    def score(config: SpectralConfig) -> float:
        rows = [{"metrics": metrics(spectral_prediction(city, config)[0], city["mask"])} for city in training]
        return float(aggregate(rows)["f1"])
    hardcoded = max((SpectralConfig(mode="hardcoded", ndvi_drop=vi, ndbi_rise=bi, use_cloud_mask=False) for vi in HARDCODED_NDVI_GRID for bi in HARDCODED_NDBI_GRID), key=score)
    percentile = max((SpectralConfig(mode="percentile", percentile=value, use_cloud_mask=False) for value in PERCENTILE_GRID), key=score)
    warn_grid_edges("hardcoded", hardcoded)
    warn_grid_edges("percentile", percentile)
    return [("hardcoded", hardcoded), ("otsu", SpectralConfig(mode="otsu", use_cloud_mask=False)), ("percentile", percentile)]


def warn_grid_edges(name: str, config: SpectralConfig) -> None:
    """Print a warning when a selected train configuration is on a search edge."""
    edges = []
    if config.mode == "hardcoded":
        if config.ndvi_drop in (HARDCODED_NDVI_GRID[0], HARDCODED_NDVI_GRID[-1]):
            edges.append(f"ndvi_drop={config.ndvi_drop}")
        if config.ndbi_rise in (HARDCODED_NDBI_GRID[0], HARDCODED_NDBI_GRID[-1]):
            edges.append(f"ndbi_rise={config.ndbi_rise}")
    elif config.mode == "percentile" and config.percentile in (PERCENTILE_GRID[0], PERCENTILE_GRID[-1]):
        edges.append(f"percentile={config.percentile}")
    if edges:
        print(f"WARNING: selected {name} value(s) at search-grid edge: {', '.join(edges)}")


def run_key(city: str, pipeline: str, configuration: str, *, preprocess: str | None = None, grid_values: dict | None = None) -> str:
    """Stable identity for resume entries; legacy rows without this key are ignored."""
    return json.dumps({"city": city, "pipeline": pipeline, "configuration": configuration, "preprocess": preprocess, "grid_values": grid_values}, sort_keys=True, separators=(",", ":"))


def load_rows(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.is_file() else []


def checkpoint(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2))


def cnn_prediction(data: dict, preprocess: str = "reflectance") -> np.ndarray:
    try:
        from app import run_inference_arrays
        rgb_a, rgb_b = preprocess_rgb_pair(data["rgb_raw_a"], data["rgb_raw_b"], preprocess)
        result = run_inference_arrays(rgb_a, rgb_b)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Pipeline A CNN requires model.onnx: {exc}") from exc
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(result["mask_base64"]))), dtype=np.uint8) > 0


def write_table(output: Path, rows: list[dict], *, stem: str = "oscd_results_v2") -> None:
    metric_rows = [row for row in rows if "metrics" in row]
    lines = ["| City | Pipeline | Config | Selection | Predicted fraction | True fraction | Precision | Recall | F1 | IoU | OA |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in metric_rows:
        value = row["metrics"]
        lines.append(f"| {row['city']} | {row['pipeline']} | {row['configuration']} | {row.get('selection', '')} | {row['predicted_fraction']:.4f} | {row['true_fraction']:.4f} | {value['precision']:.4f} | {value['recall']:.4f} | {value['f1']:.4f} | {value['iou']:.4f} | {value['overall_accuracy']:.4f} |")
    grouped = itertools.groupby(sorted(metric_rows, key=lambda row: (row["pipeline"], row["configuration"])), lambda row: (row["pipeline"], row["configuration"]))
    for (pipeline, configuration), group in grouped:
        value = aggregate(list(group)); lines.append(f"| aggregate | {pipeline} | {configuration} |  | {value['predicted_fraction']:.4f} | {value['true_fraction']:.4f} | {value['precision']:.4f} | {value['recall']:.4f} | {value['f1']:.4f} | {value['iou']:.4f} | {value['overall_accuracy']:.4f} |")
    (output / f"{stem}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/content/oscd"))
    parser.add_argument("--images-root", type=Path)
    parser.add_argument("--train-labels-root", type=Path)
    parser.add_argument("--test-labels-root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("/content/drive/MyDrive/oscd/results"))
    args = parser.parse_args()
    images = args.images_root or args.root / "images" / "Onera Satellite Change Detection dataset - Images"
    train_labels = args.train_labels_root or args.root / "train_labels" / "Onera Satellite Change Detection dataset - Train Labels"
    test_labels = args.test_labels_root or args.root / "Onera Satellite Change Detection dataset - Test Labels"
    train_cities, test_cities = read_city_list(images / "train.txt"), read_city_list(images / "test.txt")
    if tuple(test_cities) != OFFICIAL_TEST_CITIES:
        raise ValueError(f"test.txt does not match official OSCD test cities: {test_cities}")
    print(f"Train cities ({len(train_cities)}): {', '.join(train_cities)}")
    print(f"Test cities ({len(test_cities)}): {', '.join(test_cities)}")
    training = [load_city(images, train_labels, city) for city in tqdm(train_cities, desc="Validating train cities")]
    configs = select_configs(training)
    print("Selected spectral configs from TRAIN split only:", {name: config.__dict__ for name, config in configs})
    cnn_scores = {}
    for preprocess in CNN_PREPROCESS_VARIANTS:
        train_rows = []
        for city_data in tqdm(training, desc=f"Selecting CNN preprocessing: {preprocess}"):
            prediction = cnn_prediction(city_data, preprocess=preprocess)
            train_rows.append({"metrics": metrics(prediction, city_data["mask"])})
        cnn_scores[preprocess] = float(aggregate(train_rows)["f1"])
    chosen_preprocess = max(CNN_PREPROCESS_VARIANTS, key=lambda name: cnn_scores[name])
    print(f"CNN preprocessing selected on TRAIN split only: {chosen_preprocess} (pooled F1={cnn_scores[chosen_preprocess]:.4f}); scores={cnn_scores}")
    result_path = args.output / "oscd_results_v2.json"; rows = load_rows(result_path)
    finished = {row.get("run_key") for row in rows}
    for city in tqdm(test_cities, desc="Scoring test cities"):
        data = load_city(images, test_labels, city)
        for name, config in configs:
            grid_values = config.__dict__
            key = run_key(city, "spectral", name, grid_values=grid_values)
            if key not in finished:
                prediction, thresholds = spectral_prediction(data, config)
                row_metrics = metrics(prediction, data["mask"])
                rows.append({"run_key": key, "city": city, "pipeline": "spectral", "configuration": name, "grid_values": grid_values, "metrics": row_metrics, "predicted_fraction": row_metrics["predicted_fraction"], "true_fraction": row_metrics["true_fraction"], "thresholds": thresholds, "split": "test"})
                finished.add(key)
                checkpoint(result_path, rows)
        for preprocess in CNN_PREPROCESS_VARIANTS:
            selection = "chosen on train" if preprocess == chosen_preprocess else "other"
            configuration = f"pipeline_a_cnn_{preprocess}_{selection.replace(' ', '_')}"
            key = run_key(city, "cnn", configuration, preprocess=preprocess)
            if key not in finished:
                prediction = cnn_prediction(data, preprocess=preprocess)
                row_metrics = metrics(prediction, data["mask"])
                rows.append({"run_key": key, "city": city, "pipeline": "cnn", "configuration": configuration, "preprocess": preprocess, "selection": selection, "metrics": row_metrics, "predicted_fraction": row_metrics["predicted_fraction"], "true_fraction": row_metrics["true_fraction"], "split": "test"})
                finished.add(key)
                checkpoint(result_path, rows)
    write_table(args.output, rows, stem="oscd_results_v2")


if __name__ == "__main__":
    main()
