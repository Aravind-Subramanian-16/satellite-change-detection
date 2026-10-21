"""Profile-specific index math and change-mask composition on top of spectral_pipeline."""
from __future__ import annotations

import numpy as np

from postprocess import apply_mmu, morphological_cleanup
from profiles import ProfileConfig
from spectral_pipeline import SpectralConfig, cloud_mask, decode_indices, detect_from_indices

INDEX_KEYS = ("ndvi", "ndbi", "nbr", "ndmi", "bsi")


def _decode_band(encoded: np.ndarray) -> np.ndarray:
    return (np.asarray(encoded, dtype=np.float32) / 255.0 - 0.5) * 2.0


def indices_from_encoded(indices: np.ndarray, indices_ext: np.ndarray | None) -> tuple[dict, np.ndarray | None]:
    """Decode NDVI/NDBI/SCL plus optional NBR/NDMI/BSI from the Evalscript PNGs."""
    ndvi, ndbi, scl = decode_indices(indices)
    data = {"ndvi": ndvi, "ndbi": ndbi, "nbr": None, "ndmi": None, "bsi": None}
    if indices_ext is not None and getattr(indices_ext, "size", 0):
        ext = np.asarray(indices_ext, dtype=np.float32)
        if ext.ndim != 3 or ext.shape[-1] < 3:
            raise ValueError("indices_ext must be an HxWx3 encoded image")
        if ext.shape[:2] != ndvi.shape:
            raise ValueError("indices and indices_ext must have identical spatial dimensions")
        data["nbr"] = _decode_band(ext[..., 0])
        data["ndmi"] = _decode_band(ext[..., 1])
        data["bsi"] = _decode_band(ext[..., 2])
    return data, scl


def indices_from_bands(before: dict, after: dict) -> tuple[dict, dict]:
    """Compute the five indices from Sentinel-2 reflectance bands (OSCD/synthetic)."""
    def one(bands: dict) -> dict:
        blue = np.asarray(bands["B02"], dtype=np.float32)
        red = np.asarray(bands["B04"], dtype=np.float32)
        nir = np.asarray(bands["B08"], dtype=np.float32)
        swir1 = np.asarray(bands["B11"], dtype=np.float32)
        swir2 = np.asarray(bands["B12"], dtype=np.float32)
        eps = 1e-6
        return {
            "ndvi": (nir - red) / np.maximum(nir + red, eps),
            "ndbi": (swir1 - nir) / np.maximum(swir1 + nir, eps),
            "nbr": (nir - swir2) / np.maximum(nir + swir2, eps),
            "ndmi": (nir - swir1) / np.maximum(nir + swir1, eps),
            "bsi": ((swir1 + red) - (nir + blue)) / np.maximum((swir1 + red) + (nir + blue), eps),
        }

    return one(before), one(after)


def _required_indices(config: ProfileConfig, profile_key: str) -> tuple[str, ...]:
    if profile_key == "general":
        return ("ndvi", "ndbi")
    return tuple(config.indices)


def _finite(*arrays) -> np.ndarray:
    valid = None
    for array in arrays:
        current = np.isfinite(array)
        valid = current if valid is None else (valid & current)
    return np.ones_like(arrays[0], dtype=bool) if valid is None else valid


def detect_profile(
    indices_a: dict,
    indices_b: dict,
    profile: ProfileConfig,
    scl_a: np.ndarray | None = None,
    scl_b: np.ndarray | None = None,
    mmu_ha: float | None = None,
    pixel_area_m2: float = 100.0,
    cleanup: bool = False,
    normalise: bool = False,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (change mask, invalid cloud mask, reproducible metadata)."""
    required = _required_indices(profile, profile.key)
    for key in required:
        if indices_a.get(key) is None or indices_b.get(key) is None:
            raise ValueError(
                f"Profile '{profile.key}' needs the {key.upper()} index, which is missing "
                "from the scene response. The extended indices layer may be unavailable."
            )
    arrays = [indices_a[key] for key in required] + [indices_b[key] for key in required]
    if len({array.shape for array in arrays}) != 1:
        raise ValueError("Profile index arrays must share the same shape")

    if normalise:
        from radiometric import match_pair

        for key in required:
            indices_b = dict(indices_b)
            indices_b[key] = match_pair(indices_a[key], indices_b[key])

    invalid = (
        cloud_mask(scl_a, scl_b, include_shadow=True)
        if scl_a is not None and scl_b is not None
        else np.zeros(arrays[0].shape, dtype=bool)
    )
    valid = ~invalid & _finite(*arrays)
    t = profile.thresholds
    flags: dict[str, int] = {}

    if profile.key == "general":
        mask, invalid, meta = detect_from_indices(
            indices_a["ndvi"],
            indices_a["ndbi"],
            indices_b["ndvi"],
            indices_b["ndbi"],
            scl_a,
            scl_b,
            SpectralConfig(
                mode="hardcoded",
                ndvi_drop=float(t.get("ndvi_drop", -0.15)),
                ndbi_rise=float(t.get("ndbi_rise", 0.10)),
            ),
        )
        effective_mmu = profile.mmu_ha if mmu_ha is None else mmu_ha
        if effective_mmu:
            mask, mmu_info = apply_mmu(mask, pixel_area_m2, effective_mmu)
        else:
            mmu_info = {"mmu_ha": 0.0, "min_pixels": 0, "removed_components": 0}
        if cleanup:
            mask = morphological_cleanup(mask, open_size=3, close_size=3)
        meta.update(
            {
                "profile": profile.key,
                "mmu": mmu_info,
                "changed_percent": float(np.asarray(mask).mean() * 100.0),
                "valid_percent": float(valid.mean() * 100.0),
            }
        )
        return np.asarray(mask, dtype=np.uint8), invalid, meta

    if profile.key == "agriculture":
        d_ndvi = indices_b["ndvi"] - indices_a["ndvi"]
        d_ndmi = indices_b["ndmi"] - indices_a["ndmi"]
        stress = (d_ndmi < -float(t["ndmi_drop"])) & (d_ndvi < -float(t["stress_ndvi_drop"]))
        vegetation_loss = d_ndvi < -float(t["ndvi_drop"])
        mask = (stress | vegetation_loss) & valid
        flags = {"cropland_stress": int(stress.sum()), "vegetation_loss": int(vegetation_loss.sum())}
    elif profile.key == "deforestation":
        nbr_drop = indices_a["nbr"] - indices_b["nbr"]
        ndvi_drop = indices_a["ndvi"] - indices_b["ndvi"]
        vegetated_before = indices_a["ndvi"] >= float(profile.vegetated_before_ndvi or 0.30)
        mask = (nbr_drop > float(t["nbr_drop"])) & (ndvi_drop > float(t["ndvi_drop"])) & vegetated_before & valid
        flags = {
            "vegetated_before_pixels": int(vegetated_before.sum()),
            "nbr_drop_pixels": int(((nbr_drop > float(t["nbr_drop"])) & valid).sum()),
        }
    elif profile.key == "builtup":
        d_ndbi = indices_b["ndbi"] - indices_a["ndbi"]
        d_bsi = indices_b["bsi"] - indices_a["bsi"]
        d_ndvi = indices_b["ndvi"] - indices_a["ndvi"]
        built_ndbi = (d_ndbi > float(t["ndbi_rise"])) & (d_ndvi < -0.05)
        built_bsi = (d_bsi > float(t["bsi_rise"])) & (d_ndvi < -float(t["ndvi_drop"]))
        mask = (built_ndbi | built_bsi) & valid
        flags = {"ndbi_cue": int(built_ndbi.sum()), "bare_soil_cue": int(built_bsi.sum())}
    elif profile.key == "roads":
        mask, invalid, meta = detect_from_indices(
            indices_a["ndvi"],
            indices_a["ndbi"],
            indices_b["ndvi"],
            indices_b["ndbi"],
            scl_a,
            scl_b,
            SpectralConfig(
                mode="hardcoded",
                ndvi_drop=float(t.get("ndvi_drop", -0.15)),
                ndbi_rise=float(t.get("ndbi_rise", 0.10)),
            ),
        )
        meta.update(
            {
                "profile": "roads",
                "road_context_only": True,
                "mmu": {"mmu_ha": 0.0, "min_pixels": 0, "removed_components": 0},
                "changed_percent": float(mask.mean() * 100.0),
                "valid_percent": float(valid.mean() * 100.0),
                "flags": flags,
            }
        )
        return np.asarray(mask, dtype=np.uint8), invalid, meta
    else:  # pragma: no cover - get_profile prevents this
        raise ValueError(f"Unsupported profile: {profile.key}")

    effective_mmu = profile.mmu_ha if mmu_ha is None else mmu_ha
    mask, mmu_info = apply_mmu(mask.astype(np.uint8), pixel_area_m2, effective_mmu)
    if cleanup:
        mask = morphological_cleanup(mask, open_size=3, close_size=3)
        mask, mmu_info_after = apply_mmu(mask, pixel_area_m2, effective_mmu)
        mmu_info = {**mmu_info, **mmu_info_after}
    meta = {
        "profile": profile.key,
        "mode": "profile",
        "thresholds": dict(t),
        "mmu": mmu_info,
        "cloud_mask_enabled": scl_a is not None and scl_b is not None,
        "masked_percent": float(invalid.mean() * 100.0),
        "valid_percent": float(valid.mean() * 100.0),
        "changed_percent": float(mask.mean() * 100.0),
        "flags": flags,
        "radiometric_normalisation": bool(normalise),
        "morphological_cleanup": bool(cleanup),
    }
    return mask.astype(np.uint8), invalid, meta
