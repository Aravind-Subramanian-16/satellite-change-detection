"""Object-level cleanup shared by analysis profiles and D2 experiments."""
from __future__ import annotations

import numpy as np

try:
    from scipy import ndimage as _ndimage
    _HAVE_SCIPY = True
except ImportError:
    _HAVE_SCIPY = False

try:
    import cv2 as _cv2
    _HAVE_CV2 = True
except ImportError:
    _HAVE_CV2 = False


def label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    binary = np.asarray(mask).astype(np.uint8)
    if _HAVE_CV2:
        count, labels = _cv2.connectedComponents(binary, connectivity=8)
        return labels, count - 1
    if _HAVE_SCIPY:
        labels, count = _ndimage.label(binary, structure=np.ones((3, 3), dtype=int))
        return labels, int(count)
    labels = np.zeros(binary.shape, dtype=np.int32)
    current = 0
    height, width = binary.shape
    for row in range(height):
        for col in range(width):
            if binary[row, col] and not labels[row, col]:
                current += 1
                stack = [(row, col)]
                labels[row, col] = current
                while stack:
                    r, c = stack.pop()
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            nr, nc = r + dr, c + dc
                            if (
                                0 <= nr < height
                                and 0 <= nc < width
                                and binary[nr, nc]
                                and not labels[nr, nc]
                            ):
                                labels[nr, nc] = current
                                stack.append((nr, nc))
    return labels, current


def apply_mmu(mask: np.ndarray, pixel_area_m2: float, mmu_ha: float) -> tuple[np.ndarray, dict]:
    """Remove connected components smaller than the minimum mapping unit."""
    mask = np.asarray(mask).astype(np.uint8)
    info = {"mmu_ha": float(mmu_ha or 0.0), "min_pixels": 0, "removed_components": 0}
    if not mmu_ha or mmu_ha <= 0 or pixel_area_m2 <= 0:
        return mask, info
    min_pixels = max(1, int(np.ceil(float(mmu_ha) * 10_000.0 / float(pixel_area_m2))))
    info["min_pixels"] = min_pixels
    labels, count = label_components(mask)
    if count == 0:
        return mask, info
    sizes = np.bincount(labels.ravel())
    keep = np.zeros(sizes.size, dtype=bool)
    keep[1:] = sizes[1:] >= min_pixels
    filtered = keep[labels].astype(np.uint8)
    info["removed_components"] = int(sum(1 for index in range(1, sizes.size) if sizes[index] < min_pixels))
    return filtered, info


def morphological_cleanup(
    mask: np.ndarray,
    open_size: int = 0,
    close_size: int = 0,
) -> np.ndarray:
    """Optional opening then closing; a no-op when both sizes are zero."""
    binary = np.asarray(mask).astype(np.uint8)
    if open_size and open_size > 0:
        binary = _morph(binary, open_size, "open")
    if close_size and close_size > 0:
        binary = _morph(binary, close_size, "close")
    return binary.astype(np.uint8)


def _morph(binary: np.ndarray, size: int, operation: str) -> np.ndarray:
    size = int(size)
    if _HAVE_CV2:
        kernel = np.ones((size, size), dtype=np.uint8)
        if operation == "open":
            return _cv2.morphologyEx(binary, _cv2.MORPH_OPEN, kernel)
        return _cv2.morphologyEx(binary, _cv2.MORPH_CLOSE, kernel)
    if _HAVE_SCIPY:
        structure = np.ones((size, size), dtype=bool)
        if operation == "open":
            return _ndimage.binary_opening(binary > 0, structure=structure).astype(np.uint8)
        return _ndimage.binary_closing(binary > 0, structure=structure).astype(np.uint8)
    return binary
