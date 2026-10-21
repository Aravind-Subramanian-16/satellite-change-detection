"""Pure AOI, season and scene-ranking helpers (no network, easy to test)."""
from __future__ import annotations

import math
from datetime import date, datetime, timezone

M_PER_DEG_LAT = 111_320.0


def parse_bbox(value) -> list[float]:
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must contain four comma-separated numbers")
        value = parts
    try:
        bbox = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValueError("bbox must contain four numbers") from exc
    if len(bbox) != 4:
        raise ValueError("bbox must contain [min_lon, min_lat, max_lon, max_lat]")
    min_lon, min_lat, max_lon, max_lat = bbox
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise ValueError("bbox coordinates are out of range or min >= max")
    return bbox


def bbox_dimensions_km(bbox: list[float]) -> tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = math.radians((min_lat + max_lat) / 2.0)
    width_km = (max_lon - min_lon) * M_PER_DEG_LAT * math.cos(mid_lat) / 1000.0
    height_km = (max_lat - min_lat) * M_PER_DEG_LAT / 1000.0
    return max(width_km, 0.0), max(height_km, 0.0)


def bbox_area_km2(bbox: list[float]) -> float:
    width_km, height_km = bbox_dimensions_km(bbox)
    return width_km * height_km


def expected_pixels(
    bbox: list[float],
    resolution_m: float = 10.0,
    max_px: int = 1024,
    min_px: int = 64,
) -> dict:
    """Output raster dimensions at native 10 m, capped for payload safety."""
    width_km, height_km = bbox_dimensions_km(bbox)
    width_px = int(round(width_km * 1000.0 / resolution_m))
    height_px = int(round(height_km * 1000.0 / resolution_m))
    scale = 1.0
    if max(width_px, height_px) > max_px:
        scale = max_px / max(width_px, height_px)
    width = max(min_px, min(max_px, int(round(width_px * scale))))
    height = max(min_px, min(max_px, int(round(height_px * scale))))
    pixel_x = width_km * 1000.0 / width if width else 0.0
    pixel_y = height_km * 1000.0 / height if height else 0.0
    return {
        "native_width_px": width_px,
        "native_height_px": height_px,
        "analysis_width_px": width,
        "analysis_height_px": height,
        "pixel_size_x_m": round(pixel_x, 2),
        "pixel_size_y_m": round(pixel_y, 2),
        "capped": bool(scale < 1.0),
    }


def validate_aoi(bbox, max_km: float = 10.0, max_px: int = 1024) -> dict:
    """Return a structured AOI check; never silently clips the user's box."""
    bbox = parse_bbox(bbox)
    width_km, height_km = bbox_dimensions_km(bbox)
    area_km2 = width_km * height_km
    pixels = expected_pixels(bbox, max_px=max_px)
    problems = []
    if width_km <= 0 or height_km <= 0:
        problems.append("AOI has zero width or height.")
    if width_km > max_km or height_km > max_km:
        problems.append(
            f"AOI is {width_km:.2f} km × {height_km:.2f} km; the limit is "
            f"{max_km:g} km per side. Draw a smaller box or zoom in."
        )
    if area_km2 > max_km * max_km + 1e-9:
        problems.append(f"AOI area {area_km2:.2f} km² exceeds {max_km * max_km:g} km².")
    return {
        "valid": not problems,
        "bbox": bbox,
        "width_km": round(width_km, 3),
        "height_km": round(height_km, 3),
        "area_km2": round(area_km2, 3),
        "expected_pixels": pixels,
        "max_km": max_km,
        "message": " ".join(problems) if problems else "AOI accepted.",
    }


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValueError(f"Invalid date '{value}'; expected YYYY-MM-DD") from exc


def season_of(value: str | date) -> str:
    """Meteorological season, simple and reproducible."""
    month = _parse_date(value).month
    if month in (12, 1, 2):
        return "DJF"
    if month in (3, 4, 5):
        return "MAM"
    if month in (6, 7, 8):
        return "JJA"
    return "SON"


SEASON_NAMES = {"DJF": "Dec–Feb", "MAM": "Mar–May", "JJA": "Jun–Aug", "SON": "Sep–Nov"}


def season_warning(date_before: str | date, date_after: str | date) -> str | None:
    before, after = _parse_date(date_before), _parse_date(date_after)
    first, second = season_of(before), season_of(after)
    if first == second:
        return None
    return (
        f"Before ({before}) is in {SEASON_NAMES[first]} while after ({after}) is in "
        f"{SEASON_NAMES[second]}. Vegetation, crops and surface moisture change with "
        "season; a single pair can confuse phenology with damage."
    )


def _parse_datetime(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _geometry_bbox(geometry: dict | None) -> list[float] | None:
    if not geometry:
        return None
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    points: list[tuple[float, float]] = []

    def walk(node):
        if not isinstance(node, (list, tuple)) or not node:
            return
        if len(node) >= 2 and all(isinstance(value, (int, float)) for value in node[:2]):
            points.append((float(node[0]), float(node[1])))
            return
        for child in node:
            walk(child)

    walk(coordinates)
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def _intersection_area(a: list[float], b: list[float]) -> float:
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return width * height


def coverage_fraction(feature: dict, bbox: list[float]) -> float:
    """AOI fraction covered by the scene footprint (bbox approximation)."""
    scene_bbox = _geometry_bbox(feature.get("geometry"))
    aoi_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    if not scene_bbox or aoi_area <= 0:
        return 1.0
    return max(0.0, min(1.0, _intersection_area(scene_bbox, bbox) / aoi_area))


def rank_scenes(
    features: list[dict],
    bbox: list[float],
    target_date: str | date,
    window_days: int = 30,
    top: int = 5,
) -> list[dict]:
    """Rank catalog features by AOI coverage, cloud cover and date closeness."""
    target = _parse_date(target_date)
    window = max(1, int(window_days))
    ranked = []
    for feature in features or []:
        properties = feature.get("properties") or {}
        stamp = properties.get("datetime") or feature.get("datetime")
        if not stamp:
            continue
        try:
            when = _parse_datetime(stamp)
        except ValueError:
            continue
        scene_date = when.date()
        cloud = properties.get("eo:cloud_cover")
        cloud = float(cloud) if isinstance(cloud, (int, float)) else 100.0
        cloud = min(max(cloud, 0.0), 100.0)
        coverage = coverage_fraction(feature, bbox)
        days = abs((scene_date - target).days)
        closeness = max(0.0, 1.0 - days / window)
        score = 0.5 * coverage + 0.3 * (1.0 - cloud / 100.0) + 0.2 * closeness
        scene_id = str(feature.get("id") or properties.get("s2:product_uri") or "")
        ranked.append(
            {
                "id": scene_id,
                "datetime": when.isoformat().replace("+00:00", "Z"),
                "date": scene_date.isoformat(),
                "cloud_cover_percent": round(cloud, 2),
                "coverage_percent": round(coverage * 100.0, 2),
                "coverage_method": "geometry bbox ∩ AOI bbox / AOI bbox (approximation)",
                "days_from_target": days,
                "score": round(score, 4),
                "score_components": {
                    "coverage": round(coverage, 4),
                    "cloud": round(1.0 - cloud / 100.0, 4),
                    "closeness": round(closeness, 4),
                },
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["datetime"], row["id"]))
    for rank, row in enumerate(ranked[:top], start=1):
        row["rank"] = rank
        row["recommended"] = rank == 1
    return ranked[:top]


def date_window(date_value: str, window_days: int) -> tuple[str, str]:
    """Return the inclusive ISO datetime range for the Copernicus catalog."""
    target = _parse_date(date_value)
    start = datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc)
    from datetime import timedelta

    start = start - timedelta(days=int(window_days))
    end = datetime.combine(target, datetime.max.time(), tzinfo=timezone.utc)
    end = end + timedelta(days=int(window_days))
    return (
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
