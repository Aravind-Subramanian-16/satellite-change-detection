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
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spectral_pipeline import SpectralConfig, detect_from_indices

OFFICIAL_TEST_CITIES = ("brasilia", "montpellier", "norcia", "rio", "saclay_w", "valencia", "dubai", "lasvegas", "milano", "chongqing")
BANDS = ("B02", "B03", "B04", "B08", "B11")


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
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0, "overall_accuracy": (tp + tn) / (tp + fp + fn + tn), "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def aggregate(rows: list[dict]) -> dict[str, float | int]:
    counts = {name: sum(row["metrics"][name] for row in rows) for name in ("tp", "fp", "fn", "tn")}
    predicted = np.array([1] * (counts["tp"] + counts["fp"]) + [0] * (counts["fn"] + counts["tn"]))
    label = np.array([1] * counts["tp"] + [0] * counts["fp"] + [1] * counts["fn"] + [0] * counts["tn"])
    return metrics(predicted, label)


def raster(path: Path) -> np.ndarray:
    try:
        import rasterio
    except ImportError as exc:
        raise RuntimeError("OSCD evaluation requires rasterio; install requirements.txt") from exc
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


def load_city(images_root: Path, labels_root: Path, city: str) -> dict:
    before_dir, after_dir = images_root / city / "imgs_1_rect", images_root / city / "imgs_2_rect"
    label_path = labels_root / city / "cm" / "cm.png"
    if not label_path.is_file():
        raise FileNotFoundError(f"{city}: missing change label {label_path}")
    label = np.asarray(Image.open(label_path).convert("L"), dtype=np.uint8)
    values = set(np.unique(label).tolist())
    if not values.issubset({0, 255}):
        raise ValueError(f"{city}: cm.png must contain only 0 and 255, got {sorted(values)}")
    bands, mismatches = {}, []
    for time, directory in (("before", before_dir), ("after", after_dir)):
        for band in BANDS:
            path = band_path(directory, band)
            image = raster(path)
            bands[time, band] = image
            if image.shape != label.shape:
                mismatches.append(f"{time} {band}: band {image.shape}, label {label.shape} ({path})")
    if mismatches:
        raise ValueError(f"{city}: raster/label dimensions differ; refusing to resize:\n" + "\n".join(mismatches))
    def indices(time: str) -> tuple[np.ndarray, np.ndarray]:
        nir, red, swir = bands[time, "B08"], bands[time, "B04"], bands[time, "B11"]
        return (nir - red) / np.maximum(nir + red, 1e-6), (swir - nir) / np.maximum(swir + nir, 1e-6)
    ndvi_a, ndbi_a = indices("before"); ndvi_b, ndbi_b = indices("after")
    return {"city": city, "mask": label == 255, "ndvi_a": ndvi_a, "ndbi_a": ndbi_a, "ndvi_b": ndvi_b, "ndbi_b": ndbi_b, "rgb_a": rgb(bands["before", "B04"], bands["before", "B03"], bands["before", "B02"]), "rgb_b": rgb(bands["after", "B04"], bands["after", "B03"], bands["after", "B02"])}


def spectral_prediction(data: dict, config: SpectralConfig) -> tuple[np.ndarray, dict]:
    prediction, _, thresholds = detect_from_indices(data["ndvi_a"], data["ndbi_a"], data["ndvi_b"], data["ndbi_b"], config=config)
    return prediction, thresholds


def select_configs(training: list[dict]) -> list[tuple[str, SpectralConfig]]:
    def score(config: SpectralConfig) -> float:
        rows = [{"metrics": metrics(spectral_prediction(city, config)[0], city["mask"])} for city in training]
        return float(aggregate(rows)["f1"])
    hardcoded = max((SpectralConfig(mode="hardcoded", ndvi_drop=vi, ndbi_rise=bi, use_cloud_mask=False) for vi in (-0.30, -0.20, -0.15, -0.10, -0.05) for bi in (0.05, 0.10, 0.15, 0.20)), key=score)
    percentile = max((SpectralConfig(mode="percentile", percentile=value, use_cloud_mask=False) for value in (80.0, 85.0, 90.0, 95.0, 97.5)), key=score)
    return [("hardcoded", hardcoded), ("otsu", SpectralConfig(mode="otsu", use_cloud_mask=False)), ("percentile", percentile)]


def load_rows(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.is_file() else []


def checkpoint(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2))


def cnn_prediction(data: dict) -> np.ndarray:
    try:
        from app import run_inference_arrays
        result = run_inference_arrays(data["rgb_a"], data["rgb_b"])
    except FileNotFoundError as exc:
        raise RuntimeError(f"Pipeline A CNN requires model.onnx: {exc}") from exc
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(result["mask_base64"]))), dtype=np.uint8) > 0


def write_table(output: Path, rows: list[dict]) -> None:
    metric_rows = [row for row in rows if "metrics" in row]
    lines = ["| City | Pipeline | Config | Precision | Recall | F1 | IoU | OA |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for row in metric_rows:
        value = row["metrics"]
        lines.append(f"| {row['city']} | {row['pipeline']} | {row['configuration']} | {value['precision']:.4f} | {value['recall']:.4f} | {value['f1']:.4f} | {value['iou']:.4f} | {value['overall_accuracy']:.4f} |")
    grouped = itertools.groupby(sorted(metric_rows, key=lambda row: (row["pipeline"], row["configuration"])), lambda row: (row["pipeline"], row["configuration"]))
    for (pipeline, configuration), group in grouped:
        value = aggregate(list(group)); lines.append(f"| aggregate | {pipeline} | {configuration} | {value['precision']:.4f} | {value['recall']:.4f} | {value['f1']:.4f} | {value['iou']:.4f} | {value['overall_accuracy']:.4f} |")
    (output / "oscd_results.md").write_text("\n".join(lines) + "\n")
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
    print("Selected from TRAIN split only:", {name: config.__dict__ for name, config in configs})
    result_path = args.output / "oscd_results.json"; rows = load_rows(result_path)
    finished = {(row["city"], row["pipeline"], row["configuration"]) for row in rows}
    for city in tqdm(test_cities, desc="Scoring test cities"):
        data = load_city(images, test_labels, city)
        for name, config in configs:
            key = (city, "spectral", name)
            if key not in finished:
                prediction, thresholds = spectral_prediction(data, config)
                rows.append({"city": city, "pipeline": "spectral", "configuration": name, "metrics": metrics(prediction, data["mask"]), "thresholds": thresholds, "split": "test"})
                checkpoint(result_path, rows)
        key = (city, "cnn", "pipeline_a_cnn")
        if key not in finished:
            prediction = cnn_prediction(data)
            rows.append({"city": city, "pipeline": "cnn", "configuration": "pipeline_a_cnn", "metrics": metrics(prediction, data["mask"]), "split": "test"})
            checkpoint(result_path, rows)
    write_table(args.output, rows)


if __name__ == "__main__":
    main()
