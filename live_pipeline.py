"""Live Sentinel-2 workflow: AOI -> best scenes -> profile detection -> provenance."""
from __future__ import annotations

import io
import os
from datetime import date

import numpy as np
from PIL import Image

from change_reasoner import reason_regions
from compositing import median_composite
from copernicus_client import CopernicusError, MissingCredentialsError, NoScenesError
from osm_roads import OsmError, osm_road_context
from profiles import get_profile, profile_public
from profiles.detection import detect_profile, indices_from_encoded
from provenance import build_provenance
from scene_selection import rank_scenes, season_warning, validate_aoi
from spectral_pipeline import CLOUD_CLASSES

DEFAULT_WINDOW_DAYS = int(os.environ.get("DEFAULT_WINDOW_DAYS", "30"))
CLOUD_WARN_PERCENT = float(os.environ.get("CLOUD_WARN_PERCENT", "30"))
MAX_AOI_KM = float(os.environ.get("MAX_AOI_KM", "10"))
MAX_ANALYSIS_PX = int(os.environ.get("MAX_ANALYSIS_PX", "1024"))


class FullyMaskedError(RuntimeError):
    def __init__(self, message: str, details: dict):
        super().__init__(message)
        self.details = details


def cloud_fraction(scl: np.ndarray | None) -> float:
    if scl is None or np.asarray(scl).size == 0:
        return 0.0
    return float(np.isin(np.asarray(scl), CLOUD_CLASSES).mean() * 100.0)


def _decode_png(data: bytes) -> np.ndarray:
    if not data:
        return np.zeros((0, 0, 0), dtype=np.uint8)
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.uint8)


def _encode(image: Image.Image) -> str:
    import base64

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _decode_bundle(bundle: dict) -> dict:
    if not bundle.get("rgb") or not bundle.get("indices"):
        raise CopernicusError("Scene download is missing RGB or indices.")
    rgb = _decode_png(bundle["rgb"])
    indices = _decode_png(bundle["indices"]).astype(np.float32)
    ext = _decode_png(bundle.get("indices_ext") or b"").astype(np.float32)
    if indices.shape[:2] != rgb.shape[:2]:
        raise CopernicusError(
            f"Scene layers have different sizes: RGB {rgb.shape[:2]} vs indices {indices.shape[:2]}."
        )
    if ext.size and ext.shape[:2] != rgb.shape[:2]:
        raise CopernicusError(
            f"Scene layers have different sizes: RGB {rgb.shape[:2]} vs extended indices {ext.shape[:2]}."
        )
    decoded, scl = indices_from_encoded(indices, ext if ext.size else None)
    return {"rgb": rgb, "indices": indices, "ext": ext if ext.size else None, "decoded": decoded, "scl": scl}


def _scene_row_to_feature(row: dict) -> dict:
    return {
        "id": row["id"],
        "properties": {
            "datetime": row["datetime"],
            "eo:cloud_cover": row.get("cloud_cover_percent"),
        },
    }


def choose_scene_window(
    client,
    bbox: list[float],
    target_date: str,
    window_days: int,
    scene_id: str | None = None,
) -> tuple[dict, list[dict]]:
    features = client.search_scenes(bbox, target_date, window_days=window_days)
    ranked = rank_scenes(features, bbox, target_date, window_days=window_days, top=len(features))
    if not ranked:
        raise NoScenesError(f"No usable scenes near {target_date}.")
    if scene_id:
        for row in ranked:
            if row["id"] == scene_id:
                return row, ranked
        raise ValueError(
            f"Scene '{scene_id}' is not in the ±{window_days}-day window around {target_date}. "
            "Refresh the scene list and choose one of the returned scenes."
        )
    return ranked[0], ranked


def _fetch_window(
    client,
    bbox: list[float],
    ranked: list[dict],
    chosen: dict,
    output_size: tuple[int, int],
    composite_n: int,
) -> dict:
    count = max(1, min(int(composite_n), 5))
    selected = [chosen]
    if count > 1:
        for row in ranked:
            if row["id"] != chosen["id"] and len(selected) < count:
                selected.append(row)
    bundles = []
    for row in selected:
        bundle = client.fetch_scene(bbox, _scene_row_to_feature(row), output_size=output_size)
        decoded = _decode_bundle(bundle)
        bundle["decoded_bundle"] = decoded
        bundle["cloud_fraction"] = cloud_fraction(decoded["scl"])
        bundle["rank_row"] = row
        bundles.append(bundle)
    primary = bundles[0]
    result = {
        "primary": primary,
        "scenes": bundles,
        "cloud_fraction": primary["cloud_fraction"],
    }
    if len(bundles) > 1:
        masks = [np.isin(bundle["decoded_bundle"]["scl"], CLOUD_CLASSES) for bundle in bundles]
        rgb = median_composite([bundle["decoded_bundle"]["rgb"] for bundle in bundles], masks)
        indices = median_composite([bundle["decoded_bundle"]["indices"] for bundle in bundles], masks)
        ext = median_composite([bundle["decoded_bundle"]["ext"] for bundle in bundles], masks)
        rgb = np.nan_to_num(rgb, nan=0.0).clip(0, 255).astype(np.uint8)
        indices = np.nan_to_num(indices, nan=0.0).clip(0, 255).astype(np.float32)
        ext = np.nan_to_num(ext, nan=0.0).clip(0, 255).astype(np.float32)
        decoded, scl = indices_from_encoded(indices, ext if ext.size else None)
        result["decoded_bundle"] = {"rgb": rgb, "indices": indices, "ext": ext, "decoded": decoded, "scl": scl}
        result["cloud_fraction"] = cloud_fraction(scl)
        result["composite_count"] = len(bundles)
    else:
        result["decoded_bundle"] = primary["decoded_bundle"]
        result["composite_count"] = 1
    return result


def _public_scene(bundle: dict) -> dict:
    row = bundle["rank_row"]
    return {
        "id": bundle.get("scene_id") or row.get("id"),
        "datetime": bundle.get("datetime") or row.get("datetime"),
        "date": str(bundle.get("datetime") or row.get("datetime"))[:10],
        "catalog_cloud_cover_percent": row.get("cloud_cover_percent"),
        "aoi_cloud_fraction_percent": round(bundle.get("cloud_fraction", 0.0), 2),
        "coverage_percent": row.get("coverage_percent"),
        "score": row.get("score"),
    }


def _next_best(ranked: list[dict], chosen_id: str, limit: int = 3) -> list[dict]:
    return [row for row in ranked if row["id"] != chosen_id][:limit]


def _enrich_regions(regions: list[dict], pixel_area_m2: float) -> list[dict]:
    for region in regions:
        region["area_m2"] = round(float(region["pixel_area"]) * pixel_area_m2, 2)
        region["area_ha"] = round(region["area_m2"] / 10_000.0, 3)
    return regions


def _summary(percent: float, regions: list[dict], profile_label: str, place: str, before: str, after: str) -> str:
    if percent < 5:
        severity = "minimal"
    elif percent < 15:
        severity = "moderate"
    else:
        severity = "significant"
    valid = [region for region in regions if region.get("change_type") != "Possible cloud interference"]
    if valid:
        area_by_type: dict[str, float] = {}
        for region in valid:
            area_by_type[region["change_type"]] = area_by_type.get(region["change_type"], 0.0) + region.get("area_m2", 0.0)
        dominant = max(area_by_type.items(), key=lambda item: item[1])[0].lower()
    else:
        dominant = "no classified change"
    return (
        f"{profile_label} analysis of {place} between {before} and {after} shows {severity} change, "
        f"with approximately {percent:.2f}% of the analysed raster flagged — primarily {dominant}. "
        "Decision support, not ground truth."
    )


def analyse_pair(
    client,
    bbox: list[float],
    date_before: str,
    date_after: str,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    scene_before_id: str | None = None,
    scene_after_id: str | None = None,
    profile_key: str = "general",
    mmu_ha: float | None = None,
    composite_scenes: int = 1,
    normalise: bool = False,
    cleanup: bool = False,
    include_road_context: bool = False,
    cloud_warn_percent: float = CLOUD_WARN_PERCENT,
    max_aoi_km: float = MAX_AOI_KM,
    max_px: int = MAX_ANALYSIS_PX,
    place_name: str | None = None,
) -> dict:
    before_date = date.fromisoformat(str(date_before)[:10])
    after_date = date.fromisoformat(str(date_after)[:10])
    if before_date >= after_date:
        raise ValueError("date_before must be earlier than date_after.")
    aoi = validate_aoi(bbox, max_km=max_aoi_km, max_px=max_px)
    if not aoi["valid"]:
        raise ValueError(aoi["message"])
    config = get_profile(profile_key)
    pixels = aoi["expected_pixels"]
    output_size = (pixels["analysis_width_px"], pixels["analysis_height_px"])
    season_note = season_warning(date_before, date_after)
    warnings: list[dict] = []

    chosen_before, ranked_before = choose_scene_window(client, bbox, date_before, window_days, scene_before_id)
    chosen_after, ranked_after = choose_scene_window(client, bbox, date_after, window_days, scene_after_id)
    before_window = _fetch_window(client, bbox, ranked_before, chosen_before, output_size, composite_scenes)
    after_window = _fetch_window(client, bbox, ranked_after, chosen_after, output_size, composite_scenes)

    for label, window, ranked in (
        ("before", before_window, ranked_before),
        ("after", after_window, ranked_after),
    ):
        fraction = window["cloud_fraction"]
        if fraction > cloud_warn_percent:
            active_scene_id = window["primary"].get("scene_id") or window["primary"]["rank_row"]["id"]
            suggestions = _next_best(ranked, active_scene_id)
            warnings.append(
                {
                    "code": "cloud",
                    "severity": "warning",
                    "window": label,
                    "message": (
                        f"{fraction:.1f}% of the {label} AOI is cloud/shadow (SCL classes 3, 8, 9, 10), "
                        f"above the {cloud_warn_percent:g}% threshold. Results over masked pixels are unknown."
                    ),
                    "suggested_scenes": [
                        {"id": row["id"], "date": row["date"], "cloud_cover_percent": row["cloud_cover_percent"]}
                        for row in suggestions
                    ],
                }
            )
        if fraction >= 99.5:
            raise FullyMaskedError(
                f"The {label} scene is fully masked by cloud/shadow over this AOI; no valid pixels remain.",
                {
                    "window": label,
                    "cloud_fraction_percent": round(fraction, 2),
                    "candidates": ranked[:5],
                    "suggestion": "Choose another scene from the list or widen the ± window.",
                },
            )

    if season_note:
        warnings.append(
            {
                "code": "season",
                "severity": "warning" if not config.season_warning else "high",
                "message": season_note,
            }
        )
    if composite_scenes and int(composite_scenes) > 1:
        warnings.append(
            {
                "code": "experimental",
                "severity": "info",
                "message": f"Temporal median composite of {before_window['composite_count']} before and "
                f"{after_window['composite_count']} after scenes (experimental flag).",
            }
        )
    if normalise:
        warnings.append(
            {
                "code": "experimental",
                "severity": "info",
                "message": "Radiometric normalisation of indices is enabled (experimental flag).",
            }
        )

    before_bundle, after_bundle = before_window["decoded_bundle"], after_window["decoded_bundle"]
    pixel_x = float(aoi["width_km"]) * 1000.0 / output_size[0]
    pixel_y = float(aoi["height_km"]) * 1000.0 / output_size[1]
    pixel_area_m2 = pixel_x * pixel_y

    mask, invalid, meta = detect_profile(
        before_bundle["decoded"],
        after_bundle["decoded"],
        config,
        scl_a=before_bundle["scl"],
        scl_b=after_bundle["scl"],
        mmu_ha=mmu_ha,
        pixel_area_m2=pixel_area_m2,
        cleanup=cleanup,
        normalise=normalise,
    )

    regions = reason_regions(
        before_bundle["rgb"],
        after_bundle["rgb"],
        mask,
        idx_a=before_bundle["indices"],
        idx_b=after_bundle["indices"],
    )
    _enrich_regions(regions, pixel_area_m2)

    road_context = None
    if (config.show_road_context or include_road_context) and mask.any():
        try:
            road_context = osm_road_context(mask, bbox, distance_m=50.0)
        except (OsmError, ValueError) as exc:
            warnings.append(
                {"code": "osm", "severity": "warning", "message": f"OSM road context unavailable: {exc}"}
            )

    before_rgb, after_rgb = before_bundle["rgb"], after_bundle["rgb"]
    overlay = after_rgb.copy()
    overlay[mask == 1] = [255, 0, 0]
    overlay_image = Image.blend(Image.fromarray(after_rgb), Image.fromarray(overlay), alpha=0.5)
    evidence = np.maximum(
        np.maximum(before_bundle["decoded"]["ndvi"] - after_bundle["decoded"]["ndvi"], 0),
        np.maximum(after_bundle["decoded"]["ndbi"] - before_bundle["decoded"]["ndbi"], 0),
    )
    finite = np.isfinite(evidence)
    scale = float(np.nanpercentile(evidence, 99)) if finite.any() else 0.0
    confidence = np.clip(evidence / scale, 0, 1) if scale > 1e-8 else np.zeros_like(evidence)
    valid_pixels = max(1, int(np.asarray(invalid).size - np.asarray(invalid).sum()))
    percent_masked = float(np.asarray(invalid).mean() * 100.0)
    percent_changed = float(np.asarray(mask).mean() * 100.0)
    percent_changed_valid = float(np.asarray(mask).sum() / valid_pixels * 100.0)

    public_profile = profile_public(config.key)
    scenes = {
        "before": _public_scene({**before_window["primary"], "rank_row": chosen_before}),
        "after": _public_scene({**after_window["primary"], "rank_row": chosen_after}),
    }
    provenance = build_provenance(
        "spectral",
        profile=config.key,
        thresholds=dict(config.thresholds),
        scene_ids=[scenes["before"]["id"], scenes["after"]["id"]],
        dates={"before": date_before, "after": date_after},
        percent_masked=percent_masked,
        extra={
            "options": {
                "window_days": int(window_days),
                "composite_scenes": int(composite_scenes),
                "normalise": bool(normalise),
                "cleanup": bool(cleanup),
                "mmu_ha": meta.get("mmu", {}).get("mmu_ha"),
                "cloud_warn_percent": float(cloud_warn_percent),
            },
            "aoi": {"bbox": bbox, "area_km2": aoi["area_km2"]},
            "pixel_size_m": [round(pixel_x, 2), round(pixel_y, 2)],
        },
    )
    result = {
        "percent_changed": percent_changed,
        "percent_changed_valid": percent_changed_valid,
        "percent_cloud_masked": percent_masked,
        "image_a_base64": _encode(Image.fromarray(before_rgb)),
        "image_b_base64": _encode(Image.fromarray(after_rgb)),
        "mask_base64": _encode(Image.fromarray(mask * 255)),
        "overlay_base64": _encode(overlay_image),
        "confidence_base64": _encode(Image.fromarray((confidence * 255).astype(np.uint8))),
        "change_regions": regions,
        "thresholds": meta,
        "pipeline": "spectral",
        "profile": config.key,
        "profile_label": config.label,
        "profile_description": config.description,
        "profile_notes": list(config.report_wording) + list(config.honesty_notes),
        "validation_status": public_profile["validation_status"],
        "validation_short": public_profile["validation_short"],
        "validation_evidence": public_profile["validation_evidence"],
        "display_metrics": public_profile["display_metrics"],
        "cloud_coverage_before": scenes["before"]["catalog_cloud_cover_percent"],
        "cloud_coverage_after": scenes["after"]["catalog_cloud_cover_percent"],
        "aoi_cloud_fraction_before": round(before_window["cloud_fraction"], 2),
        "aoi_cloud_fraction_after": round(after_window["cloud_fraction"], 2),
        "scenes": scenes,
        "scene_candidates": {"before": ranked_before[:5], "after": ranked_after[:5]},
        "warnings": warnings,
        "season_warning": season_note,
        "aoi": aoi,
        "image_shape": [int(after_rgb.shape[0]), int(after_rgb.shape[1])],
        "road_context": road_context,
        "provenance": provenance,
        "date_before": date_before,
        "date_after": date_after,
        "resolved_bbox": bbox,
        "summary_sentence": _summary(
            percent_changed,
            regions,
            config.label,
            place_name or "the selected location",
            date_before,
            date_after,
        ),
    }
    return result


def build_ndvi_timeline(
    client,
    bbox: list[float],
    dates: list[str],
    *,
    window_days: int = 10,
    max_aoi_km: float = MAX_AOI_KM,
) -> dict:
    """Optional 3–5 date NDVI timeline for the agriculture profile."""
    if not 3 <= len(dates) <= 5:
        raise ValueError("The NDVI timeline needs 3 to 5 dates.")
    aoi = validate_aoi(bbox, max_km=max_aoi_km, max_px=512)
    if not aoi["valid"]:
        raise ValueError(aoi["message"])
    unique = sorted(dict.fromkeys(str(item)[:10] for item in dates))
    if len(unique) != len(dates):
        raise ValueError("Timeline dates must be unique.")
    points = []
    for target in unique:
        chosen, _ = choose_scene_window(client, bbox, target, window_days)
        bundle = client.fetch_scene(
            bbox,
            _scene_row_to_feature(chosen),
            output_size=(256, 256),
        )
        decoded = _decode_bundle(bundle)
        scl = decoded["scl"]
        valid = ~np.isin(scl, CLOUD_CLASSES) & np.isfinite(decoded["decoded"]["ndvi"])
        values = decoded["decoded"]["ndvi"][valid]
        points.append(
            {
                "requested_date": target,
                "scene_date": str(bundle.get("datetime") or chosen["datetime"])[:10],
                "scene_id": bundle.get("scene_id") or chosen["id"],
                "ndvi_mean": round(float(values.mean()), 4) if values.size else None,
                "valid_percent": round(float(valid.mean() * 100.0), 2),
            }
        )
    return {
        "points": points,
        "profile": "agriculture",
        "note": (
            "Cloud/shadow-masked mean NDVI per date. Few dates cannot resolve phenology; "
            "interpret with local crop calendars. Unvalidated, qualitative only."
        ),
        "aoi": aoi,
    }
