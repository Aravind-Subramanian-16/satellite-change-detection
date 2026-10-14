"""Memory-safe overlapping tiles and feathered reconstruction for Pipeline A."""
from __future__ import annotations
from collections.abc import Callable
import numpy as np

def positions(length: int, tile: int = 256, overlap: int = 32) -> list[int]:
    if length <= tile: return [0]
    stride = tile - overlap
    starts = list(range(0, length - tile + 1, stride))
    if starts[-1] != length - tile: starts.append(length - tile)
    return starts

def tiled_predict(image_a: np.ndarray, image_b: np.ndarray, predict: Callable[[np.ndarray, np.ndarray], np.ndarray], tile: int = 256, overlap: int = 32) -> np.ndarray:
    """Apply `predict` to RGB tiles and average overlapping probabilities."""
    if image_a.shape != image_b.shape or image_a.ndim != 3: raise ValueError("images must be equally sized HxWxC arrays")
    h, w = image_a.shape[:2]; total = np.zeros((h, w), np.float32); weight = np.zeros((h, w), np.float32)
    for y in positions(h, tile, overlap):
        for x in positions(w, tile, overlap):
            a, b = image_a[y:y+tile, x:x+tile], image_b[y:y+tile, x:x+tile]
            ph, pw = a.shape[:2]
            if ph != tile or pw != tile:
                a = np.pad(a, ((0, tile-ph), (0, tile-pw), (0, 0)), mode="edge"); b = np.pad(b, ((0, tile-ph), (0, tile-pw), (0, 0)), mode="edge")
            prediction = np.asarray(predict(a, b), dtype=np.float32)[:ph, :pw]
            total[y:y+ph, x:x+pw] += prediction; weight[y:y+ph, x:x+pw] += 1
    return total / np.maximum(weight, 1)
