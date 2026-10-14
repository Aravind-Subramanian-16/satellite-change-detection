"""
change_reasoner.py
──────────────────
Deterministic, explainable per-region change classification.
No external APIs, no ML model, no LLM — pure image statistics + thresholds.

Public API
----------
reason_regions(img_a_rgb, img_b_rgb, binary_mask)
    img_a_rgb  : np.ndarray  uint8 [H, W, 3]   before image (RGB, 0-255)
    img_b_rgb  : np.ndarray  uint8 [H, W, 3]   after  image (RGB, 0-255)
    binary_mask: np.ndarray  uint8 [H, W]       1=changed, 0=unchanged
    returns    : list[dict]  one entry per connected component (sorted by area ↓)

Each dict:
    bounding_box    : [x, y, w, h]  (x=col, y=row in image coords)
    pixel_area      : int
    change_type     : str
    confidence_label: str           "High" | "Medium" | "Low"
    stats           : dict          raw feature values (always included)
"""

from __future__ import annotations
import numpy as np

try:
    from scipy.ndimage import label as scipy_label
    _HAVE_SCIPY = True
except ImportError:
    _HAVE_SCIPY = False

try:
    import cv2 as _cv2
    _HAVE_CV2 = True
except ImportError:
    _HAVE_CV2 = False

# ──────────────────────────────────────────────────────────────────────────────
# Minimum component area (in pixels at whatever resolution the mask arrives).
# Lowered to 5 pixels so we don't completely filter out small individual buildings 
# (at 10m Sentinel-2 resolution, a 20x30m building is ~6 pixels).
MIN_REGION_AREA = 5

# ──────────────────────────────────────────────────────────────────────────────
# Classification thresholds (conservative — prefer "unclear" over wrong label)
# ──────────────────────────────────────────────────────────────────────────────

# Vegetation / green-ratio thresholds
# green_ratio = G / (R + G + B + 1e-6)  ∈ [0, 1]
VEGE_RATIO_HIGH   = 0.36   # region is strongly vegetated if ratio > this
VEGE_DROP_THRESH  = 0.07   # ratio must drop by at least this to call deforestation

# New-construction / uniform-grey thresholds
GREY_UNIFORMITY_THRESH  = 28.0   # std-dev of brightness in "after" crop
                                  # low = uniform = likely built surface
GREY_DOMINANCE_THRESH   = 0.40   # |R-G| + |G-B| < this fraction of mean brightness
                                  # ⟹ achromatic / grey-ish after-image crop

# Bare-soil thresholds  (warm brownish tone, medium brightness, not green)
SOIL_RED_EXCESS_THRESH  = 0.04   # after.R/mean − after.G/mean > this (warm shift)
SOIL_BRIGHT_LOW         = 60     # min brightness for bare soil (not dark shadow)
SOIL_BRIGHT_HIGH        = 190    # max brightness for bare soil (not bright roof)

# Minimum colour-shift magnitude to even attempt labelling
COLOR_SHIFT_MIN = 12.0   # Euclidean distance in RGB space; below → "unclear"

# Cloud interference thresholds
CLOUD_BRIGHT_THRESH = 190
CLOUD_UNIFORMITY_MAX = 20.0

# Water thresholds — require BOTH dark pixels AND no vegetation (NDVI < -0.05)
# Raised from 55 to 40 to avoid misclassifying dark urban pixels at 10m resolution
WATER_BRIGHT_MAX = 40
WATER_NDVI_MAX   = -0.05   # actual water has negative NDVI


# ──────────────────────────────────────────────────────────────────────────────
def _label_connected(binary_mask: np.ndarray):
    """
    Label connected components in binary_mask (uint8, values 0/1).
    Returns (labeled_array, num_components).
    Prefers cv2, falls back to scipy, then pure-numpy 4-connectivity BFS.
    """
    if _HAVE_CV2:
        n, labels = _cv2.connectedComponents(binary_mask.astype(np.uint8),
                                             connectivity=8)
        return labels, n - 1   # label 0 = background
    if _HAVE_SCIPY:
        labels, n = scipy_label(binary_mask)
        return labels, n
    # Pure-numpy fallback: simple 4-connectivity BFS
    labels = np.zeros_like(binary_mask, dtype=np.int32)
    current_label = 0
    H, W = binary_mask.shape
    for r in range(H):
        for c in range(W):
            if binary_mask[r, c] == 1 and labels[r, c] == 0:
                current_label += 1
                queue = [(r, c)]
                labels[r, c] = current_label
                while queue:
                    cr, cc = queue.pop()
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = cr+dr, cc+dc
                        if 0 <= nr < H and 0 <= nc < W and \
                           binary_mask[nr, nc] == 1 and labels[nr, nc] == 0:
                            labels[nr, nc] = current_label
                            queue.append((nr, nc))
    return labels, current_label


def _crop(img_rgb: np.ndarray, row_min, row_max, col_min, col_max) -> np.ndarray:
    """Return a sub-array, clamped to image bounds."""
    H, W = img_rgb.shape[:2]
    r0 = max(0, row_min); r1 = min(H, row_max)
    c0 = max(0, col_min); c1 = min(W, col_max)
    return img_rgb[r0:r1, c0:c1]


def _safe_mean(arr):
    return float(np.mean(arr)) if arr.size > 0 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
def _compute_stats(img_a_crop: np.ndarray, img_b_crop: np.ndarray) -> dict:
    """
    Compute interpretable color statistics for one changed region.
    All values are floats on natural scales (0-255 or 0-1 ratios).
    """
    a = img_a_crop.astype(np.float32)
    b = img_b_crop.astype(np.float32)

    # Per-channel means
    aR, aG, aB = _safe_mean(a[:,:,0]), _safe_mean(a[:,:,1]), _safe_mean(a[:,:,2])
    bR, bG, bB = _safe_mean(b[:,:,0]), _safe_mean(b[:,:,1]), _safe_mean(b[:,:,2])

    # Green ratio (vegetation proxy)  G / (R+G+B)
    veg_a = aG / (aR + aG + aB + 1e-6)
    veg_b = bG / (bR + bG + bB + 1e-6)
    veg_drop = veg_a - veg_b          # positive ⟹ green decreased

    # Brightness (luminance proxy)
    bright_a = 0.299*aR + 0.587*aG + 0.114*aB
    bright_b = 0.299*bR + 0.587*bG + 0.114*bB

    # Uniformity of brightness in "after" crop (low std ⟹ flat/uniform surface)
    brightness_b = 0.299*b[:,:,0] + 0.587*b[:,:,1] + 0.114*b[:,:,2]
    uniformity_std_b = float(np.std(brightness_b)) if brightness_b.size > 0 else 255.0

    # Achromatic score in "after": low |R-G| + |G-B| relative to brightness ⟹ grey
    mean_bright_b = float(np.mean(brightness_b)) + 1e-6
    achromatic_b  = (abs(bR - bG) + abs(bG - bB)) / mean_bright_b

    # Overall colour-shift magnitude (Euclidean in RGB space)
    color_shift = float(np.sqrt((bR-aR)**2 + (bG-aG)**2 + (bB-aB)**2))

    # Warm-shift (red excess in after vs before, proxy for bare soil)
    red_excess_b = (bR - bG) / (mean_bright_b)   # positive ⟹ warm/reddish

    return {
        "veg_ratio_before":    round(veg_a, 4),
        "veg_ratio_after":     round(veg_b, 4),
        "veg_ratio_drop":      round(veg_drop, 4),
        "brightness_before":   round(bright_a, 2),
        "brightness_after":    round(bright_b, 2),
        "uniformity_std_b":    round(uniformity_std_b, 2),
        "achromatic_score_b":  round(achromatic_b, 4),
        "color_shift_mag":     round(color_shift, 2),
        "red_excess_after":    round(red_excess_b, 4),
    }


# ──────────────────────────────────────────────────────────────────────────────
def _classify(stats: dict) -> tuple[str, str]:
    """
    Apply threshold rules in priority order.
    Returns (change_type: str, confidence_label: str).

    Design principle: conservative — only assign a specific label when
    multiple independent signals agree.  Otherwise return fallback.
    """
    veg_before     = stats["veg_ratio_before"]
    veg_drop       = stats["veg_ratio_drop"]
    shift          = stats["color_shift_mag"]
    unif_std       = stats["uniformity_std_b"]
    achromatic     = stats["achromatic_score_b"]
    bright_b       = stats["brightness_after"]
    red_excess     = stats["red_excess_after"]

    # ── Rule 0: Possible cloud interference ───────────────────────────────
    # Very bright and uniform in either before or after image
    bright_a = stats["brightness_before"]
    # We don't have uniformity_std_a, but high brightness + achromatic + low std in B is a good cloud signature.
    # If the after image is extremely bright and uniform:
    if bright_b > CLOUD_BRIGHT_THRESH and unif_std < CLOUD_UNIFORMITY_MAX:
        return "Possible cloud interference", "High"
    # Or if before image was extremely bright (assuming we can't easily check its uniformity, brightness > 210 is a strong signal)
    if bright_a > 210:
        return "Possible cloud interference", "Medium"

    # Require a minimum colour shift to say anything specific
    if shift < COLOR_SHIFT_MIN:
        return "Change detected (type unclear)", "Low"

    # ── Rule 1: Water body change ─────────────────────────────────────────
    # Require: very dark pixel (brightness < 40) AND negative NDVI stored in stats
    # (avoids triggering on dark urban shadows at 10m resolution)
    ndvi_after = stats.get("ndvi_after", None)
    if bright_a < WATER_BRIGHT_MAX or bright_b < WATER_BRIGHT_MAX:
        # If we have NDVI data, require negative NDVI to confirm water
        if ndvi_after is None or ndvi_after < WATER_NDVI_MAX:
            return "Water body change", "Medium"
        # Otherwise downgrade to unclear (dark but not water-like spectrally)
        return "Change detected (type unclear)", "Low"

    # ── Rule 2: Deforestation / vegetation loss ───────────────────────────
    # Before was significantly green AND green ratio dropped substantially
    if veg_before > VEGE_RATIO_HIGH and veg_drop > VEGE_DROP_THRESH:
        # If final state is very warm/red (bare soil) or highly uniform (built), it's deforestation.
        # If it's still somewhat green, it might be agricultural.
        if stats["veg_ratio_after"] > 0.30:
            return "Agricultural land conversion", "Medium"
        
        confidence = "High" if (veg_before > 0.40 and veg_drop > 0.10) else "Medium"
        return "Deforestation / vegetation loss", confidence

    # ── Rule 3: Agricultural land conversion ──────────────────────────────
    # Before and after are both somewhat green, or toggling between soil and green
    if (0.28 < veg_before < 0.38) and (0.28 < stats["veg_ratio_after"] < 0.38) and abs(veg_drop) > 0.05:
        return "Agricultural land conversion", "Low"

    # ── Rule 4: Urban expansion / new construction ────────────────────────
    # After image is uniform (low std) AND achromatic (grey-ish)
    construction_signals = 0
    if unif_std < GREY_UNIFORMITY_THRESH:
        construction_signals += 1
    if achromatic < GREY_DOMINANCE_THRESH:
        construction_signals += 1
    if bright_b > 100:   # not dark shadow
        construction_signals += 1
    if construction_signals >= 2:
        confidence = "High" if construction_signals == 3 else "Medium"
        return "Urban expansion / new construction", confidence

    # ── Rule 5: Bare soil / land clearing ────────────────────────────────
    # After image is warm-toned, medium brightness, not green
    if (red_excess > SOIL_RED_EXCESS_THRESH
            and SOIL_BRIGHT_LOW < bright_b < SOIL_BRIGHT_HIGH
            and stats["veg_ratio_after"] < 0.34):
        return "Likely bare soil / land clearing", "Medium"

    # ── Fallback ──────────────────────────────────────────────────────────
    return "Change detected (type unclear)", "Low"


# ──────────────────────────────────────────────────────────────────────────────
def reason_regions(
    img_a_rgb: np.ndarray,
    img_b_rgb: np.ndarray,
    binary_mask: np.ndarray,
    idx_a: np.ndarray = None,
    idx_b: np.ndarray = None,
    max_regions: int = 20,
) -> list[dict]:
    """
    Main entry point.

    Parameters
    ----------
    img_a_rgb    : uint8 [H, W, 3]  before image in RGB
    img_b_rgb    : uint8 [H, W, 3]  after  image in RGB
    binary_mask  : uint8 [H, W]     1=change, 0=no-change
    idx_a        : float [H, W, 3]  Optional spectral indices before (NDVI, NDBI, SCL)
    idx_b        : float [H, W, 3]  Optional spectral indices after  (NDVI, NDBI, SCL)
    max_regions  : cap on number of components returned (largest first)

    Returns
    -------
    list of dicts, each:
        bounding_box     [x, y, w, h]  (x=col-offset, y=row-offset)
        pixel_area       int
        change_type      str
        confidence_label str
        stats            dict
    """
    assert img_a_rgb.ndim == 3 and img_a_rgb.shape[2] == 3, "img_a must be [H,W,3]"
    assert img_b_rgb.ndim == 3 and img_b_rgb.shape[2] == 3, "img_b must be [H,W,3]"
    assert binary_mask.ndim == 2, "binary_mask must be [H,W]"

    H, W = binary_mask.shape

    # Ensure images match mask spatial size
    if img_a_rgb.shape[:2] != (H, W):
        # simple nearest-neighbour resize via slicing for numpy-only path
        raise ValueError(
            f"img_a size {img_a_rgb.shape[:2]} != mask size ({H},{W}). "
            "Resize images to match the mask before calling reason_regions()."
        )

    if np.sum(binary_mask) == 0:
        return []   # no change detected at all

    labeled, n_components = _label_connected(binary_mask)

    results = []
    for label_id in range(1, n_components + 1):
        component = (labeled == label_id)
        area = int(np.sum(component))
        if area < MIN_REGION_AREA:
            continue

        rows = np.where(component.any(axis=1))[0]
        cols = np.where(component.any(axis=0))[0]
        row_min, row_max = int(rows[0]), int(rows[-1]) + 1
        col_min, col_max = int(cols[0]), int(cols[-1]) + 1

        crop_a = _crop(img_a_rgb, row_min, row_max, col_min, col_max)
        crop_b = _crop(img_b_rgb, row_min, row_max, col_min, col_max)

        # Mask pixels outside this exact component within the bounding box
        comp_bbox = component[row_min:row_max, col_min:col_max]
        # Zero-out pixels not in this component so stats are region-only
        crop_a_masked = crop_a * comp_bbox[:, :, np.newaxis]
        crop_b_masked = crop_b * comp_bbox[:, :, np.newaxis]
        # Extract only the masked pixels for stats
        idx = comp_bbox.flatten().astype(bool)
        crop_a_px = crop_a.reshape(-1, 3)[idx]
        crop_b_px = crop_b.reshape(-1, 3)[idx]
        # Wrap as (N,1,3) for _compute_stats (expects [H,W,3])
        crop_a_px = crop_a_px[:, np.newaxis, :]
        crop_b_px = crop_b_px[:, np.newaxis, :]

        stats = _compute_stats(crop_a_px, crop_b_px)

        # ── Spectral-index-aware classification (Sentinel-2 live mode) ─────
        # When NDVI/NDBI arrays are provided, use them for primary classification.
        # This bypasses the fragile RGB heuristics that fail at 10m resolution.
        if idx_a is not None and idx_b is not None:
            # Crop spectral index arrays to bounding box, same as comp_bbox
            idx_a_crop = idx_a[row_min:row_max, col_min:col_max, :]
            idx_b_crop = idx_b[row_min:row_max, col_min:col_max, :]
            # Only pixels inside this exact component
            mask_flat = comp_bbox.flatten().astype(bool)
            ndvi_a_px = ((idx_a_crop[:, :, 0].flatten() / 255.0 - 0.5) * 2.0)[mask_flat]
            ndvi_b_px = ((idx_b_crop[:, :, 0].flatten() / 255.0 - 0.5) * 2.0)[mask_flat]
            ndbi_a_px = ((idx_a_crop[:, :, 1].flatten() / 255.0 - 0.5) * 2.0)[mask_flat]
            ndbi_b_px = ((idx_b_crop[:, :, 1].flatten() / 255.0 - 0.5) * 2.0)[mask_flat]
            ndvi_a_region = float(np.mean(ndvi_a_px)) if len(ndvi_a_px) else 0.0
            ndvi_b_region = float(np.mean(ndvi_b_px)) if len(ndvi_b_px) else 0.0
            ndbi_a_region = float(np.mean(ndbi_a_px)) if len(ndbi_a_px) else 0.0
            ndbi_b_region = float(np.mean(ndbi_b_px)) if len(ndbi_b_px) else 0.0

            d_ndvi = ndvi_b_region - ndvi_a_region
            d_ndbi = ndbi_b_region - ndbi_a_region
            # Attach to stats so _classify water rule can use NDVI
            stats["ndvi_after"] = ndvi_b_region
            stats["ndvi_before"] = ndvi_a_region
            stats["ndbi_after"] = ndbi_b_region

            # Priority spectral classification:
            spectral_type = None
            spectral_conf = "Medium"
            # Water: NDVI < -0.1 in after image (strong water signal)
            if ndvi_b_region < -0.1:
                spectral_type = "Water body change"
                spectral_conf = "High" if ndvi_b_region < -0.2 else "Medium"
            # Vegetation loss: NDVI dropped significantly
            elif d_ndvi < -0.12:
                if d_ndbi > 0.05:  # Built-up also increased → construction replaced green
                    spectral_type = "Urban expansion / new construction"
                    spectral_conf = "High" if (d_ndbi > 0.12 and d_ndvi < -0.18) else "Medium"
                elif ndvi_b_region > 0.15:
                    spectral_type = "Agricultural land conversion"
                    spectral_conf = "Medium"
                else:
                    spectral_type = "Deforestation / vegetation loss"
                    spectral_conf = "High" if d_ndvi < -0.2 else "Medium"
            # Urban growth: NDBI increased without strong NDVI change
            elif d_ndbi > 0.12:
                spectral_type = "Urban expansion / new construction"
                spectral_conf = "High" if d_ndbi > 0.2 else "Medium"
            # Vegetation gain (reforestation / greening)
            elif d_ndvi > 0.12:
                spectral_type = "Vegetation gain / reforestation"
                spectral_conf = "Medium"

            if spectral_type:
                change_type, confidence = spectral_type, spectral_conf
            else:
                change_type, confidence = _classify(stats)
        else:
            change_type, confidence = _classify(stats)

        results.append({
            "bounding_box":     [col_min, row_min, col_max - col_min, row_max - row_min],
            "pixel_area":       area,
            "change_type":      change_type,
            "confidence_label": confidence,
            "stats":            stats,
        })

    # Sort by area descending, cap at max_regions
    results.sort(key=lambda x: x["pixel_area"], reverse=True)
    return results[:max_regions]
