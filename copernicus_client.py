"""Copernicus Data Space Ecosystem client: catalog search and scene download.

Credentials come only from COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET.
Tests must mock this module and never touch the network.
"""
from __future__ import annotations

import io
import os
import re
import tarfile
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta

import requests

from scene_selection import date_window, expected_pixels

AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CATALOG_URL = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
COLLECTION = "sentinel-2-l2a"

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
RETRY_ATTEMPTS = 3
RETRY_BASE_SECONDS = 0.5
RETRY_MAX_SECONDS = 4.0

EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"],
    output: [
      { id: "rgb", bands: 3, sampleType: "AUTO" },
      { id: "indices", bands: 3, sampleType: "AUTO" },
      { id: "indices_ext", bands: 3, sampleType: "AUTO" }
    ]
  };
}
function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
  let ndbi = (sample.B11 - sample.B08) / (sample.B11 + sample.B08 + 0.0001);
  let nbr = (sample.B08 - sample.B12) / (sample.B08 + sample.B12 + 0.0001);
  let ndmi = (sample.B08 - sample.B11) / (sample.B08 + sample.B11 + 0.0001);
  let bsi = ((sample.B11 + sample.B04) - (sample.B08 + sample.B02)) /
            ((sample.B11 + sample.B04) + (sample.B08 + sample.B02) + 0.0001);
  return {
    rgb: [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02],
    indices: [0.5 + ndvi / 2.0, 0.5 + ndbi / 2.0, sample.SCL / 255.0],
    indices_ext: [0.5 + nbr / 2.0, 0.5 + ndmi / 2.0, 0.5 + bsi / 2.0]
  };
}
"""


class CopernicusError(RuntimeError):
    """Upstream catalog/process/authentication failure."""


class MissingCredentialsError(ValueError):
    """Credentials are absent; a 400 with a clear hint is appropriate."""


class NoScenesError(CopernicusError):
    """No intersecting Sentinel-2 L2A scenes in the requested window."""


def _retry_delay(attempt: int, retry_after: str | None, sleep_fn) -> None:
    delay = min(RETRY_MAX_SECONDS, RETRY_BASE_SECONDS * (2 ** (attempt - 1)))
    if retry_after:
        try:
            delay = min(RETRY_MAX_SECONDS, max(delay, float(retry_after)))
        except (TypeError, ValueError):
            pass
    if delay > 0:
        sleep_fn(delay)


def _post_with_retry(url, *, sleep_fn=time.sleep, attempts: int = RETRY_ATTEMPTS, **kwargs):
    """POST with a bounded retry on timeouts and transient upstream statuses."""
    attempts = max(1, int(attempts))
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(url, **kwargs)
        except requests.exceptions.RequestException:
            if attempt >= attempts:
                raise
            _retry_delay(attempt, None, sleep_fn)
            continue
        if response.status_code in RETRYABLE_STATUS and attempt < attempts:
            _retry_delay(attempt, response.headers.get("Retry-After"), sleep_fn)
            continue
        return response
    raise AssertionError("unreachable: the final attempt either returns or raises")


class _SceneCache:
    """Thread-safe LRU cache for downloaded scene bundles with a byte budget."""

    def __init__(self, max_bytes: int, max_entries: int):
        self.max_bytes = max(0, int(max_bytes))
        self.max_entries = max(1, int(max_entries))
        self._items: OrderedDict[tuple, dict] = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    @staticmethod
    def _bundle_bytes(bundle: dict) -> int:
        total = 0
        for key in ("rgb", "indices", "indices_ext"):
            value = bundle.get(key)
            if isinstance(value, (bytes, bytearray)):
                total += len(value)
        return total + 512

    def get(self, key: tuple) -> dict | None:
        with self._lock:
            bundle = self._items.get(key)
            if bundle is None:
                self.misses += 1
                return None
            self._items.move_to_end(key)
            self.hits += 1
            return dict(bundle)

    def put(self, key: tuple, bundle: dict) -> None:
        size = self._bundle_bytes(bundle)
        if size > self.max_bytes:
            return
        with self._lock:
            if key in self._items:
                self._bytes -= self._bundle_bytes(self._items.pop(key))
            while self._items and (self._bytes + size > self.max_bytes or len(self._items) >= self.max_entries):
                _, evicted = self._items.popitem(last=False)
                self._bytes -= self._bundle_bytes(evicted)
                self.evictions += 1
            self._items[key] = dict(bundle)
            self._bytes += size

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._bytes = 0

    def stats(self) -> dict:
        with self._lock:
            return {
                "entries": len(self._items),
                "bytes": self._bytes,
                "max_bytes": self.max_bytes,
                "max_entries": self.max_entries,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
            }


def _cache_limits() -> tuple[int, int]:
    def _number(name: str, fallback: float) -> int:
        try:
            return max(0, int(float(os.environ.get(name, fallback))))
        except (TypeError, ValueError):
            return int(fallback)

    return _number("SCENE_CACHE_MB", 64) * 1024 * 1024, _number("SCENE_CACHE_ENTRIES", 32)


_scene_cache: _SceneCache | None = None
_cache_lock = threading.Lock()


def get_scene_cache() -> _SceneCache:
    global _scene_cache
    with _cache_lock:
        if _scene_cache is None:
            max_bytes, max_entries = _cache_limits()
            _scene_cache = _SceneCache(max_bytes, max_entries)
        return _scene_cache


def reset_scene_cache(*, max_bytes: int | None = None, max_entries: int | None = None) -> _SceneCache:
    global _scene_cache
    with _cache_lock:
        defaults = _cache_limits()
        _scene_cache = _SceneCache(
            defaults[0] if max_bytes is None else max_bytes,
            defaults[1] if max_entries is None else max_entries,
        )
        return _scene_cache


def _scene_cache_key(bbox, scene: dict, size: tuple[int, int]) -> tuple:
    return (
        tuple(round(float(value), 6) for value in bbox),
        str(scene.get("id") or ""),
        str(scene.get("datetime") or (scene.get("properties") or {}).get("datetime") or ""),
        int(size[0]),
        int(size[1]),
    )


def make_bbox_square(bbox):
    """Legacy helper: expand the shorter side to the longer one, minimum 2.56 km."""
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = (min_lat + max_lat) / 2.0
    import math

    deg_lon_to_m = 111320.0 * math.cos(math.radians(mid_lat))
    width_m = (max_lon - min_lon) * deg_lon_to_m
    height_m = (max_lat - min_lat) * 111320.0
    max_dim_m = max(width_m, height_m, 2560.0)
    target_lon_span = max_dim_m / deg_lon_to_m
    target_lat_span = max_dim_m / 111320.0
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0
    return [
        center_lon - target_lon_span / 2.0,
        center_lat - target_lat_span / 2.0,
        center_lon + target_lon_span / 2.0,
        center_lat + target_lat_span / 2.0,
    ]


def _clean_datetime(value: str) -> datetime:
    text = re.sub(r"\.\d+", "", str(value))
    text = re.sub(r"([+-]\d{2}:\d{2}|Z)$", "", text)
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S")


class CopernicusClient:
    def __init__(self):
        self.client_id = os.environ.get("COPERNICUS_CLIENT_ID")
        self.client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET")
        self._access_token = None
        self._token_expiry = 0.0

    def _get_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise MissingCredentialsError(
                "Copernicus credentials (COPERNICUS_CLIENT_ID, COPERNICUS_CLIENT_SECRET) "
                "are missing. Set them in the environment or .env; upload mode still works."
            )
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            response = _post_with_retry(AUTH_URL, data=payload, timeout=10)
        except requests.exceptions.RequestException as exc:
            raise CopernicusError(f"Network error authenticating with Copernicus: {exc}") from exc
        if response.status_code != 200:
            raise CopernicusError(
                f"Copernicus authentication failed: HTTP {response.status_code} - {response.text[:300]}"
            )
        data = response.json()
        self._access_token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
        return self._access_token

    def search_scenes(self, bbox, date_str: str, window_days: int = 30, limit: int = 50) -> list[dict]:
        """Return raw Sentinel-2 L2A catalog features intersecting the AOI."""
        token = self._get_token()
        start, end = date_window(date_str, int(window_days))
        payload = {
            "bbox": list(bbox),
            "datetime": f"{start}/{end}",
            "collections": [COLLECTION],
            "limit": max(1, min(int(limit), 100)),
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            response = _post_with_retry(CATALOG_URL, headers=headers, json=payload, timeout=20)
        except requests.exceptions.RequestException as exc:
            raise CopernicusError(f"Network error querying the Copernicus catalog: {exc}") from exc
        if response.status_code != 200:
            raise CopernicusError(
                f"Copernicus catalog error: HTTP {response.status_code} - {response.text[:300]}"
            )
        features = response.json().get("features", [])
        if not features:
            raise NoScenesError(
                f"No Sentinel-2 L2A scenes intersect the AOI between {start[:10]} and "
                f"{end[:10]}. Try a wider ± window or a different date."
            )
        return features

    def fetch_scene(self, bbox, scene: dict, output_size: tuple[int, int] | None = None) -> dict:
        """Download RGB + encoded indices + extended indices for one catalog scene."""
        token = self._get_token()
        stamp = scene.get("datetime") or (scene.get("properties") or {}).get("datetime")
        if not stamp:
            raise CopernicusError("Scene metadata has no datetime; cannot request the Process API.")
        when = _clean_datetime(stamp)
        p_from = (when - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        p_to = (when + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        width, height = output_size or (
            expected_pixels(list(bbox))["analysis_width_px"],
            expected_pixels(list(bbox))["analysis_height_px"],
        )
        cache_key = _scene_cache_key(bbox, scene, (width, height))
        cache = get_scene_cache()
        cached = cache.get(cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached
        payload = {
            "input": {
                "bounds": {
                    "bbox": list(bbox),
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": COLLECTION,
                        "dataFilter": {"timeRange": {"from": p_from, "to": p_to}},
                    }
                ],
            },
            "output": {
                "width": int(width),
                "height": int(height),
                "responses": [
                    {"identifier": "rgb", "format": {"type": "image/png"}},
                    {"identifier": "indices", "format": {"type": "image/png"}},
                    {"identifier": "indices_ext", "format": {"type": "image/png"}},
                ],
            },
            "evalscript": EVALSCRIPT,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/tar",
        }
        try:
            response = _post_with_retry(PROCESS_URL, headers=headers, json=payload, timeout=60)
        except requests.exceptions.RequestException as exc:
            raise CopernicusError(f"Network error or timeout fetching the scene: {exc}") from exc
        if response.status_code != 200:
            raise CopernicusError(
                f"Sentinel Hub Process API error: HTTP {response.status_code} - {response.text[:300]}"
            )
        try:
            with tarfile.open(fileobj=io.BytesIO(response.content)) as archive:
                rgb_bytes = archive.extractfile("rgb.png").read()
                indices_bytes = archive.extractfile("indices.png").read()
                ext_member = archive.extractfile("indices_ext.png")
                ext_bytes = ext_member.read() if ext_member is not None else b""
        except (tarfile.TarError, KeyError, AttributeError) as exc:
            raise CopernicusError(f"Could not read the Process API TAR response: {exc}") from exc
        properties = scene.get("properties") or {}
        bundle = {
            "rgb": rgb_bytes,
            "indices": indices_bytes,
            "indices_ext": ext_bytes,
            "cloud_cover": properties.get("eo:cloud_cover"),
            "scene_id": scene.get("id"),
            "datetime": stamp,
            "bbox": list(bbox),
            "width": int(width),
            "height": int(height),
        }
        cache.put(cache_key, bundle)
        return bundle

    def _search_best_scene(self, bbox, base_date_str: str, window_days: int = 5):
        """Legacy helper retained for callers that expect (from, to, cloud)."""
        from scene_selection import rank_scenes

        features = self.search_scenes(bbox, base_date_str, window_days=window_days)
        ranked = rank_scenes(features, list(bbox), base_date_str, window_days=window_days, top=1)
        if not ranked:
            raise NoScenesError(f"No usable Sentinel-2 scenes near {base_date_str}.")
        best = ranked[0]
        when = _clean_datetime(best["datetime"])
        p_from = (when - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        p_to = (when + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return p_from, p_to, best["cloud_cover_percent"]

    def fetch_satellite_image(self, bbox, date_str):
        """Legacy tuple API (rgb_bytes, indices_bytes, cloud_cover) used by tests/scripts."""
        square = make_bbox_square(bbox)
        features = self.search_scenes(square, date_str, window_days=5)
        from scene_selection import rank_scenes

        ranked = rank_scenes(features, square, date_str, window_days=5, top=1)
        if not ranked:
            raise NoScenesError(f"No Sentinel-2 scenes found near {date_str}.")
        scene = next(
            (feature for feature in features if str(feature.get("id")) == ranked[0]["id"]),
            features[0],
        )
        bundle = self.fetch_scene(square, scene, output_size=(256, 256))
        return bundle["rgb"], bundle["indices"], ranked[0]["cloud_cover_percent"]


_client: CopernicusClient | None = None


def get_client() -> CopernicusClient:
    global _client
    if _client is None:
        _client = CopernicusClient()
    return _client


def reset_client() -> None:
    global _client
    _client = None


def fetch_satellite_image(bbox, date_str):
    return get_client().fetch_satellite_image(bbox, date_str)
