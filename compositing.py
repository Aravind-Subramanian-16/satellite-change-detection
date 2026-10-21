"""Temporal median compositing of the clearest scenes (Phase D2b, behind a flag)."""
from __future__ import annotations

import warnings

import numpy as np


def median_composite(arrays: list[np.ndarray], masks: list[np.ndarray] | None = None) -> np.ndarray:
    """Per-pixel median, excluding masked values; all-masked pixels become NaN."""
    if not arrays:
        raise ValueError("median_composite needs at least one array")
    stack = np.stack([np.asarray(array, dtype=np.float32) for array in arrays])
    if masks is not None:
        mask_stack = np.stack([np.asarray(mask, dtype=bool) for mask in masks])
        if mask_stack.shape != stack.shape:
            if stack.ndim == mask_stack.ndim + 1 and stack.shape[:-1] == mask_stack.shape:
                mask_stack = np.broadcast_to(mask_stack[..., None], stack.shape)
            else:
                raise ValueError("masks must match the array shape")
        stack = np.where(mask_stack, np.nan, stack)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(stack, axis=0).astype(np.float32)


def clear_fraction(scl: np.ndarray, invalid_classes=(3, 8, 9, 10)) -> float:
    scl = np.asarray(scl)
    return float((~np.isin(scl, invalid_classes)).mean() * 100.0)
