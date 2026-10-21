"""Optional learned pixel-change pipeline, loaded only when explicitly requested.

Training data and model artifacts live outside git. The explainable spectral
pipeline remains the default; this module never imports or mutates the CNN
weights (`best_model.pt` / `model.onnx`).
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np

from learned_features import BAND_KEYS, build_pixel_features

MODEL_PATH = Path(os.environ.get("LEARNED_MODEL_PATH", "artifacts/learned_pixel_model.joblib"))
_CACHE: dict = {"path": None, "mtime_ns": None, "bundle": None}
_ERROR: str | None = None


class LearnedModelUnavailable(RuntimeError):
    """The optional joblib model is missing or unusable; spectral paths still work."""


def is_enabled() -> bool:
    """The learned endpoint is opt-in via ENABLE_LEARNED_MODEL."""
    return os.environ.get("ENABLE_LEARNED_MODEL", "").strip().lower() in {"1", "true", "yes", "on"}


def model_status(attempt_load: bool = False) -> dict:
    path = MODEL_PATH
    info = {
        "enabled": is_enabled(),
        "present": path.is_file(),
        "path": str(path),
        "loaded": _CACHE["bundle"] is not None,
        "error": _ERROR,
        "validation_status": "experimental; trained on OSCD training cities only",
    }
    if not path.is_file():
        info["hint"] = (
            "Run benchmarks/train_pixel_classifier.py on OSCD train cities (Colab) and set "
            "LEARNED_MODEL_PATH to the resulting joblib file. The spectral pipeline is unaffected."
        )
        return info
    info["size_bytes"] = path.stat().st_size
    if attempt_load:
        try:
            bundle = load_bundle()
        except LearnedModelUnavailable as exc:
            info["error"] = str(exc)
        else:
            info.update(
                {
                    "loaded": True,
                    "threshold": float(bundle["threshold"]),
                    "feature_count": len(bundle["feature_names"]),
                    "metadata": bundle.get("metadata") or {},
                    "error": None,
                }
            )
    return info


def load_bundle(path: str | Path | None = None, force: bool = False) -> dict:
    global _ERROR
    target = Path(path or MODEL_PATH)
    if not target.is_file():
        message = (
            f"No learned pixel model at {target}. Train it on OSCD train cities or set "
            "LEARNED_MODEL_PATH. The spectral/live pipeline is unaffected."
        )
        _ERROR = message
        raise LearnedModelUnavailable(message)
    mtime_ns = target.stat().st_mtime_ns
    if (
        not force
        and _CACHE["bundle"] is not None
        and _CACHE["path"] == str(target)
        and _CACHE["mtime_ns"] == mtime_ns
    ):
        return _CACHE["bundle"]
    try:
        import joblib

        bundle = joblib.load(target)
    except Exception as exc:
        message = f"Could not load learned model {target}: {type(exc).__name__}: {exc}"
        _ERROR = message
        raise LearnedModelUnavailable(message) from exc
    if not isinstance(bundle, dict):
        raise LearnedModelUnavailable("Learned model file must contain a joblib dict bundle")
    missing = [key for key in ("model", "threshold", "feature_names") if key not in bundle]
    if missing:
        raise LearnedModelUnavailable(f"Learned model bundle is missing: {', '.join(missing)}")
    threshold = float(bundle["threshold"])
    if not 0.0 <= threshold <= 1.0 or not np.isfinite(threshold):
        raise LearnedModelUnavailable("Learned model threshold must be finite and within [0, 1]")
    if not hasattr(bundle["model"], "predict_proba"):
        raise LearnedModelUnavailable("Learned model does not expose predict_proba()")
    bundle["threshold"] = threshold
    bundle["feature_names"] = tuple(str(name) for name in bundle["feature_names"])
    _CACHE.update({"path": str(target), "mtime_ns": mtime_ns, "bundle": bundle})
    _ERROR = None
    return bundle


def reset_cache() -> None:
    global _ERROR
    _CACHE.update({"path": None, "mtime_ns": None, "bundle": None})
    _ERROR = None


def predict_change(
    bands_before: dict,
    bands_after: dict,
    *,
    bundle: dict | None = None,
    threshold: float | None = None,
    chunk_pixels: int = 200_000,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (binary change mask, probability map, reproducible metadata)."""
    stack, names = build_pixel_features(bands_before, bands_after)
    bundle = bundle or load_bundle()
    expected = tuple(bundle["feature_names"])
    if names != expected:
        raise ValueError(
            "Feature layout changed since training: "
            f"expected {len(expected)} features, built {len(names)}. Retrain the model."
        )
    cutoff = float(bundle["threshold"] if threshold is None else threshold)
    if not 0.0 <= cutoff <= 1.0 or not np.isfinite(cutoff):
        raise ValueError("threshold must be finite and within [0, 1]")

    flat = stack.reshape(-1, stack.shape[-1])
    probabilities = np.empty(flat.shape[0], dtype=np.float32)
    step = max(1, int(chunk_pixels))
    for start in range(0, flat.shape[0], step):
        probabilities[start : start + step] = bundle["model"].predict_proba(
            flat[start : start + step]
        )[:, 1].astype(np.float32)
    probability_map = probabilities.reshape(stack.shape[:2])
    mask = (probability_map >= cutoff).astype(np.uint8)
    metadata = {
        "model": _CACHE["path"] or str(MODEL_PATH),
        "threshold": cutoff,
        "feature_count": len(names),
        "predicted_fraction_percent": round(float(mask.mean() * 100.0), 4),
        "note": (
            "Experimental learned pixel classifier trained on OSCD training cities only. "
            "No test-set score is available in this checkout; not a validated land-cover product."
        ),
    }
    return mask, probability_map, metadata


def bands_from_npz(payload: bytes) -> dict:
    """Read an uploaded .npz with B02/B03/B04/B08/B11/B12 reflectance arrays."""
    try:
        archive = np.load(io.BytesIO(payload), allow_pickle=False)
    except Exception as exc:
        raise ValueError(f"Could not read .npz inputs: {exc}") from exc
    if not hasattr(archive, "files"):
        raise ValueError("Input must be a .npz archive containing Sentinel-2 band arrays")
    missing = [key for key in BAND_KEYS if key not in archive.files]
    if missing:
        raise ValueError(f"Uploaded archive is missing bands: {', '.join(missing)}")
    try:
        return {key: np.asarray(archive[key], dtype=np.float32) for key in BAND_KEYS}
    finally:
        archive.close()


def rgb_from_bands(bands: dict) -> np.ndarray:
    """False-colour-ish true RGB for visual context; not an analysis input."""
    red = np.asarray(bands["B04"], dtype=np.float32)
    green = np.asarray(bands["B03"], dtype=np.float32)
    blue = np.asarray(bands["B02"], dtype=np.float32)
    maximum = float(max(red.max(), green.max(), blue.max()))
    scale = 10000.0 if maximum > 1000.0 else 1.0
    stack = np.stack([red, green, blue], axis=-1) / scale
    return (np.clip(stack * 2.5, 0.0, 1.0) * 255.0).astype(np.uint8)
