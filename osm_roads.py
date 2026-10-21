"""Optional OpenStreetMap road context. Never a road-detection claim.

Overpass responses are cached on disk. Tests must inject elements or monkeypatch
requests; the test suite never touches the network.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests

try:
    from scipy.ndimage import distance_transform_edt
    _HAVE_SCIPY = True
except ImportError:
    _HAVE_SCIPY = False

try:
    from PIL import Image, ImageDraw
    _HAVE_PIL = True
except ImportError:
    _HAVE_PIL = False

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "satellite-change-detection/3.0 (research demo; OSM context only)"
ATTRIBUTION = "© OpenStreetMap contributors"
LICENCE = "OpenStreetMap data © OpenStreetMap contributors, ODbL 1.0"
LICENCE_NOTE = "ODbL obligations (attribution and share-alike for derived databases) must be verified before redistribution."


class OsmError(RuntimeError):
    pass


def _cache_dir() -> Path:
    return Path(os.environ.get("OSM_CACHE_DIR", "cache/osm"))


def _cache_key(bbox: list[float]) -> str:
    rounded = ",".join(f"{value:.5f}" for value in bbox)
    return hashlib.sha256(rounded.encode("utf-8")).hexdigest()[:24]


def _parse_elements(payload: dict) -> list[dict]:
    roads = []
    for element in payload.get("elements", []):
        geometry = element.get("geometry") or []
        points = [
            [float(point["lon"]), float(point["lat"])]
            for point in geometry
            if "lon" in point and "lat" in point
        ]
        if len(points) >= 2:
            tags = element.get("tags") or {}
            roads.append({"id": element.get("id"), "highway": tags.get("highway"), "points": points})
    return roads


def fetch_roads(
    bbox: list[float],
    cache_dir: str | Path | None = None,
    ttl_days: float = 7.0,
    timeout: int = 30,
) -> dict:
    """Fetch (or reuse) highway ways intersecting the AOI."""
    west, south, east, north = [float(value) for value in bbox]
    directory = Path(cache_dir) if cache_dir else _cache_dir()
    key = _cache_key([west, south, east, north])
    path = directory / f"{key}.json"
    if path.is_file():
        try:
            cached = json.loads(path.read_text())
            age_days = time.time() - float(cached.get("fetched_epoch", 0))
            if age_days <= ttl_days:
                return {**cached, "cached": True}
        except (ValueError, OSError):
            pass
    query = (
        "[out:json][timeout:25];"
        f'way["highway"]({south:.6f},{west:.6f},{north:.6f},{east:.6f});'
        "out geom;"
    )
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
    except requests.exceptions.RequestException as exc:
        raise OsmError(f"Overpass network error: {exc}") from exc
    if response.status_code != 200:
        raise OsmError(
            f"Overpass returned HTTP {response.status_code}. Try again later or disable the road overlay."
        )
    payload = response.json()
    data = {
        "bbox": [west, south, east, north],
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetched_epoch": time.time(),
        "roads": _parse_elements(payload),
        "attribution": ATTRIBUTION,
        "licence": LICENCE,
        "licence_note": LICENCE_NOTE,
        "cached": False,
    }
    try:
        directory.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data))
        temporary.replace(path)
    except OSError:
        pass
    return data


def _haversine_km(points: list[list[float]]) -> float:
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(points, points[1:]):
        radius = 6371.0088
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = phi2 - phi1
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        total += 2 * radius * math.asin(min(1.0, math.sqrt(a)))
    return total


def road_context_from_elements(
    mask: np.ndarray,
    bbox: list[float],
    roads: list[dict],
    distance_m: float = 50.0,
) -> dict:
    """Percentage of changed pixels within `distance_m` of a mapped road."""
    mask = np.asarray(mask).astype(bool)
    height, width = mask.shape
    west, south, east, north = [float(value) for value in bbox]
    lon_span, lat_span = east - west, north - south
    if lon_span <= 0 or lat_span <= 0:
        raise ValueError("bbox must have positive width and height")
    changed = int(mask.sum())
    base = {
        "distance_m": float(distance_m),
        "total_changed_pixels": changed,
        "changed_pixels_near_roads": 0,
        "percent_changed_within_distance": 0.0,
        "mapped_road_km": round(sum(_haversine_km(road["points"]) for road in roads), 3),
        "road_count": len(roads),
        "attribution": ATTRIBUTION,
        "licence": LICENCE,
        "licence_note": LICENCE_NOTE,
        "note": "Context only: roads narrower than about 20 m are mostly sub-pixel at 10 m. This is not road detection.",
    }
    if changed == 0:
        return base
    if not roads:
        return {**base, "note": base["note"] + " No mapped OSM roads intersect this AOI."}
    if not (_HAVE_PIL and _HAVE_SCIPY):
        raise OsmError("Road context needs Pillow and SciPy; install requirements.txt.")
    raster = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(raster)
    for road in roads:
        points = []
        for lon, lat in road["points"]:
            x = (lon - west) / lon_span * (width - 1)
            y = (north - lat) / lat_span * (height - 1)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=1, width=1)
    road_pixels = np.asarray(raster, dtype=bool)
    if not road_pixels.any():
        return {**base, "note": base["note"] + " Mapped roads fell outside the raster."}
    mid_lat = math.radians((south + north) / 2.0)
    pixel_x_m = lon_span * 111_320.0 * math.cos(mid_lat) / width
    pixel_y_m = lat_span * 111_320.0 / height
    distances = distance_transform_edt(~road_pixels, sampling=(pixel_y_m, pixel_x_m))
    near = mask & (distances <= distance_m)
    count = int(near.sum())
    return {
        **base,
        "changed_pixels_near_roads": count,
        "percent_changed_within_distance": round(count / changed * 100.0, 2),
        "road_pixels": int(road_pixels.sum()),
        "pixel_size_m": [round(pixel_x_m, 2), round(pixel_y_m, 2)],
    }


def osm_road_context(
    mask: np.ndarray,
    bbox: list[float],
    distance_m: float = 50.0,
    cache_dir: str | Path | None = None,
) -> dict:
    data = fetch_roads(bbox, cache_dir=cache_dir)
    result = road_context_from_elements(mask, bbox, data.get("roads", []), distance_m=distance_m)
    return {**result, "cached": data.get("cached", False), "fetched_at": data.get("fetched_at")}
