#!/usr/bin/env python3
"""Fine-tune the project CNN on OSCD TRAIN cities only.

The official test split is never loaded, and this script never reads or
overwrites ``best_model.pt`` or ``model.onnx``. It initialises a new
ImageNet-pretrained MobileNetV2 backbone and writes a separate checkpoint plus
metrics JSON under ``artifacts/`` (ignored by git). Colab/GPU recommended.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from learned_features import OFFICIAL_TEST_CITIES, assert_no_test_cities
from provenance import get_commit_hash

DEFAULT_OUTPUT = ROOT / "artifacts" / "cnn_finetuned_oscd.pt"
FORBIDDEN_NAMES = {"best_model.pt", "model.onnx"}
DEFAULT_SEED = 42
HELD_OUT_CITIES = 3
CROP_SIZE = 256
STRIDE = 128


class CheckpointGuardError(RuntimeError):
    """Refusing to touch the shipped model checkpoints."""


def assert_safe_checkpoint(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if resolved.name in FORBIDDEN_NAMES:
        raise CheckpointGuardError(
            f"Refusing to write {resolved.name}; fine-tuning must use a new checkpoint path"
        )
    for forbidden in (ROOT / "best_model.pt", ROOT / "model.onnx"):
        if resolved == forbidden.resolve():
            raise CheckpointGuardError(f"Refusing to write the shipped model file: {forbidden}")
    return resolved


def crop_coordinates(height: int, width: int, crop: int = CROP_SIZE, stride: int = STRIDE) -> list[tuple[int, int]]:
    if height < crop or width < crop:
        return []
    rows = list(range(0, height - crop + 1, max(1, stride)))
    cols = list(range(0, width - crop + 1, max(1, stride)))
    if rows[-1] != height - crop:
        rows.append(height - crop)
    if cols[-1] != width - crop:
        cols.append(width - crop)
    return [(row, col) for row in rows for col in cols]


def sample_coordinates(
    height: int,
    width: int,
    crop: int = CROP_SIZE,
    stride: int = STRIDE,
    max_crops: int = 0,
    seed: int = DEFAULT_SEED,
) -> list[tuple[int, int]]:
    coordinates = crop_coordinates(height, width, crop=crop, stride=stride)
    if max_crops > 0 and len(coordinates) > max_crops:
        rng = np.random.default_rng(seed)
        indices = np.sort(rng.choice(len(coordinates), size=max_crops, replace=False))
        coordinates = [coordinates[index] for index in indices]
    return coordinates


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
    }


def select_probability_threshold(probabilities: np.ndarray, labels: np.ndarray) -> tuple[float, list[dict]]:
    rows = []
    for threshold in np.round(np.linspace(0.05, 0.95, 19), 2):
        value = scores(np.asarray(probabilities) >= threshold, labels)
        rows.append({"threshold": float(threshold), **value})
    best = max(rows, key=lambda row: (row["f1"], row["precision"], -abs(row["threshold"] - 0.5)))
    return float(best["threshold"]), rows


def load_train_city(images_root: Path, train_labels_root: Path, city: str) -> dict:
    """Load only a training city; the guard runs before any raster is opened."""
    assert_no_test_cities([city])
    import oscd_eval

    mask, label_shape = oscd_eval.load_label(train_labels_root, city)
    acquisitions = {}
    for key, directory in (("a", "imgs_1_rect"), ("b", "imgs_2_rect")):
        root = images_root / city / directory
        bands = {band: oscd_eval.raster(oscd_eval.band_path(root, band)) for band in ("B04", "B03", "B02")}
        for band, array in bands.items():
            if array.shape != label_shape:
                raise ValueError(f"{city} {key} {band}: shape {array.shape} != label {label_shape}")
        rgb = np.clip(
            np.dstack((bands["B04"], bands["B03"], bands["B02"])) / 10000.0 * 255.0, 0, 255
        ).astype(np.uint8)
        acquisitions[key] = rgb
    return {"city": city, "a": acquisitions["a"], "b": acquisitions["b"], "mask": mask.astype(np.uint8)}


def _to_tensor(images: dict, samples: list[dict], *, training: bool, seed: int):
    import torch
    from torch.utils.data import Dataset

    class CropDataset(Dataset):
        def __init__(self) -> None:
            self.rng = np.random.default_rng(seed)

        def __len__(self) -> int:
            return len(samples)

        def __getitem__(self, index: int):
            sample = samples[index]
            city = sample["city"]
            row, col = sample["row"], sample["col"]
            crop = CROP_SIZE
            if training and self.rng.random() < 0.5:
                a = images[city]["a"][row : row + crop, col : col + crop][:, ::-1]
                b = images[city]["b"][row : row + crop, col : col + crop][:, ::-1]
                label = images[city]["mask"][row : row + crop, col : col + crop][:, ::-1]
            else:
                a = images[city]["a"][row : row + crop, col : col + crop]
                b = images[city]["b"][row : row + crop, col : col + crop]
                label = images[city]["mask"][row : row + crop, col : col + crop]
            a = torch.from_numpy(np.ascontiguousarray(a)).permute(2, 0, 1).float() / 255.0
            b = torch.from_numpy(np.ascontiguousarray(b)).permute(2, 0, 1).float() / 255.0
            mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
            a = (a - mean) / std
            b = (b - mean) / std
            label = torch.from_numpy(np.ascontiguousarray(label)).float().unsqueeze(0)
            return a, b, label

    return CropDataset()


def train(
    images: dict[str, dict],
    fit_cities: list[str],
    held_out_cities: list[str],
    *,
    output: Path,
    epochs: int = 5,
    batch_size: int = 4,
    lr: float = 1e-4,
    max_crops_per_city: int = 200,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Fine-tune and validate on TRAIN cities only; returns saved metadata."""
    import torch
    from torch.utils.data import DataLoader
    from model import MobileNetV2_3D_CDNet

    output = assert_safe_checkpoint(output)
    assert_no_test_cities(fit_cities + held_out_cities)
    if not held_out_cities:
        raise ValueError("At least one held-out TRAIN city is required for threshold selection")
    torch.manual_seed(seed)
    np.random.seed(seed)

    def samples_for(cities: list[str], max_crops: int, offset: int) -> list[dict]:
        rows = []
        for index, city in enumerate(cities):
            arrays = images[city]
            for row, col in sample_coordinates(
                arrays["a"].shape[0], arrays["a"].shape[1], max_crops=max_crops, seed=seed + offset + index
            ):
                rows.append({"city": city, "row": row, "col": col})
        return rows

    train_samples = samples_for(fit_cities, max_crops_per_city, 0)
    val_samples = samples_for(held_out_cities, max_crops_per_city, 10_000)
    if not train_samples or not val_samples:
        raise ValueError("No 256x256 crops available; check the raster sizes")
    train_loader = DataLoader(_to_tensor(images, train_samples, training=True, seed=seed), batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(_to_tensor(images, val_samples, training=False, seed=seed), batch_size=batch_size, shuffle=False, num_workers=2)

    positives = sum(int(images[city]["mask"].sum()) for city in fit_cities)
    total = sum(int(images[city]["mask"].size) for city in fit_cities)
    pos_weight = torch.tensor([min(10.0, max(1.0, (total - positives) / max(1, positives)))], dtype=torch.float32)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device))
    best = {"threshold": 0.5, "metrics": None, "epoch": -1, "state": None}
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0
        for a, b, label in train_loader:
            a, b, label = a.to(device), b.to(device), label.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(a, b)
            loss = criterion(logits, label)
            loss.backward()
            optimizer.step()
            running += float(loss.item()) * a.shape[0]
        model.eval()
        probabilities = []
        labels = []
        with torch.no_grad():
            for a, b, label in val_loader:
                logits = model(a.to(device), b.to(device))
                probabilities.append(torch.sigmoid(logits).cpu().numpy().reshape(-1))
                labels.append(label.numpy().reshape(-1))
        probability_array = np.concatenate(probabilities)
        label_array = np.concatenate(labels).astype(bool)
        threshold, sweep = select_probability_threshold(probability_array, label_array)
        value = scores(probability_array >= threshold, label_array)
        history.append({"epoch": epoch, "train_loss": running / max(1, len(train_samples)), "threshold": threshold, **value})
        print(f"epoch {epoch}/{epochs}: loss={running / max(1, len(train_samples)):.4f} val_F1={value['f1']:.4f} threshold={threshold:.2f}")
        if best["metrics"] is None or value["f1"] > best["metrics"]["f1"]:
            best = {
                "threshold": threshold,
                "metrics": value,
                "epoch": epoch,
                "state": {key: tensor.detach().cpu() for key, tensor in model.state_dict().items()},
                "sweep": sweep,
            }

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_commit": get_commit_hash(),
        "seed": int(seed),
        "fit_cities": list(fit_cities),
        "held_out_train_cities": list(held_out_cities),
        "official_test_cities_excluded": list(OFFICIAL_TEST_CITIES),
        "test_split_read": False,
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "learning_rate": float(lr),
        "crop_size": CROP_SIZE,
        "stride": STRIDE,
        "train_crops": len(train_samples),
        "validation_crops": len(val_samples),
        "selected_threshold": best["threshold"],
        "best_epoch": best["epoch"],
        "validation_metrics_at_selected_threshold": best["metrics"],
        "threshold_sweep": best["sweep"],
        "history": history,
        "note": "Held-out TRAIN-city validation only; no official test city was read or scored.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": best["state"], "threshold": best["threshold"], "metadata": metadata}, output)
    metrics_path = output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return {"checkpoint": str(output), "metrics_path": str(metrics_path), "metadata": metadata}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--train-labels-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--max-crops-per-city", type=int, default=200)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    assert_safe_checkpoint(args.output)
    split = args.images_root / "train.txt"
    if not split.is_file():
        raise FileNotFoundError(f"Missing training split: {split}")
    cities = [city.strip() for city in split.read_text().replace("\n", ",").split(",") if city.strip()]
    if len(cities) != 14:
        raise ValueError(f"Expected 14 training cities, found {len(cities)}")
    assert_no_test_cities(cities)
    rng = np.random.default_rng(args.seed)
    held_out = sorted(rng.choice(sorted(cities), size=HELD_OUT_CITIES, replace=False).tolist())
    fit_cities = sorted(set(cities) - set(held_out))
    print(f"Fit cities ({len(fit_cities)}): {', '.join(fit_cities)}")
    print(f"Held-out TRAIN cities ({len(held_out)}): {', '.join(held_out)}")
    print("Official test cities are excluded and are not read.")
    images = {city: load_train_city(args.images_root, args.train_labels_root, city) for city in cities}
    result = train(
        images,
        fit_cities,
        held_out,
        output=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_crops_per_city=args.max_crops_per_city,
        seed=args.seed,
    )
    print(json.dumps(result["metadata"]["validation_metrics_at_selected_threshold"], indent=2))
    print(f"Wrote {result['checkpoint']} and {result['metrics_path']}")
    print("No test city was read; test scoring requires the separate Phase D2.6 protocol.")


if __name__ == "__main__":
    main()
