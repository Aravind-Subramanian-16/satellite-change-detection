import os
import time
import requests
import math
import tarfile
import io
from datetime import datetime, timedelta

AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CATALOG_URL = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

def make_bbox_square(bbox):
    """
    Expands the shorter dimension of a bounding box to match the longer dimension
    in projected coordinates (meters), keeping it centered. 
    bbox format: [min_lon, min_lat, max_lon, max_lat]
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = math.radians((min_lat + max_lat) / 2.0)
    
    # Approx conversion factors
    deg_lat_to_m = 111320.0
    deg_lon_to_m = 111320.0 * math.cos(mid_lat)
    
    width_m = (max_lon - min_lon) * deg_lon_to_m
    height_m = (max_lat - min_lat) * deg_lat_to_m
    
    max_dim_m = max(width_m, height_m)
    
    # Sentinel-2 native resolution is 10m/px. A 256x256 image should ideally cover 2560m x 2560m.
    # Enforce a minimum bounding box size of 2560m to prevent massive blocky upscaling.
    max_dim_m = max(max_dim_m, 2560.0)
    
    # Target spans in degrees
    target_lon_span = max_dim_m / deg_lon_to_m
    target_lat_span = max_dim_m / deg_lat_to_m
    
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0
    
    return [
        center_lon - target_lon_span / 2.0,
        center_lat - target_lat_span / 2.0,
        center_lon + target_lon_span / 2.0,
        center_lat + target_lat_span / 2.0
    ]

class CopernicusClient:
    def __init__(self):
        self.client_id = os.environ.get("COPERNICUS_CLIENT_ID")
        self.client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET")
        self._access_token = None
        self._token_expiry = 0

    def _get_token(self):
        if not self.client_id or not self.client_secret:
            raise ValueError("Copernicus credentials (COPERNICUS_CLIENT_ID, COPERNICUS_CLIENT_SECRET) are missing. Please set them in your environment variables.")
            
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
            
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            resp = requests.post(AUTH_URL, data=payload, timeout=10)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error authenticating with Copernicus API: {str(e)}")
            
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to authenticate with Copernicus API: {resp.text}")
            
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
        return self._access_token

    def _search_best_scene(self, bbox, base_date_str):
        token = self._get_token()
        
        # ±5 day window
        base_date = datetime.strptime(base_date_str, "%Y-%m-%d")
        date_from = (base_date - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")
        date_to = (base_date + timedelta(days=5)).strftime("%Y-%m-%dT23:59:59Z")
        
        payload = {
            "bbox": bbox,
            "datetime": f"{date_from}/{date_to}",
            "collections": ["sentinel-2-l2a"],
            "limit": 20
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.post(CATALOG_URL, headers=headers, json=payload, timeout=15)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error querying Catalog API: {str(e)}")
            
        if resp.status_code != 200:
            raise RuntimeError(f"Sentinel Hub Catalog API error: HTTP {resp.status_code} - {resp.text}")
            
        data = resp.json()
        features = data.get("features", [])
        if not features:
            raise RuntimeError(f"No Sentinel-2 L2A imagery found for bbox {bbox} between {date_from} and {date_to}")
            
        # Find feature with minimum cloud cover
        best_feature = min(features, key=lambda f: f["properties"].get("eo:cloud_cover", 100.0))
        best_time_str = best_feature["properties"]["datetime"] # e.g. "2023-01-05T10:15:30Z"
        cloud_cover = best_feature["properties"].get("eo:cloud_cover", 0.0)
        
        # Parse exact time to create a tiny 1-minute window for the Process API
        # Handle formats with or without fractional seconds by replacing Z with +00:00
        best_time = datetime.fromisoformat(best_time_str.replace("Z", "+00:00"))
        p_from = (best_time - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        p_to = (best_time + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return p_from, p_to, cloud_cover

    def fetch_satellite_image(self, bbox, date_str):
        """
        Fetches a Sentinel-2 L2A true color image (B04, B03, B02) and spectral indices (NDVI, NDBI, SCL).
        Returns a tuple: (rgb_png_bytes, indices_png_bytes, cloud_coverage_percentage)
        """
        print(f"[CopernicusClient] Original requested bbox: {bbox}")
        square_bbox = make_bbox_square(bbox)
        print(f"[CopernicusClient] Padded square bbox sent to API: {square_bbox}")
        
        # Calculate dimensions in km
        lon_span = square_bbox[2] - square_bbox[0]
        lat_span = square_bbox[3] - square_bbox[1]
        print(f"[CopernicusClient] Actual geographic extent ~ {lon_span * 108.4:.2f} km x {lat_span * 111.32:.2f} km")
        
        # Find best scene in a 10 day window
        p_from, p_to, cloud_coverage = self._search_best_scene(square_bbox, date_str)
        
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/tar"
        }
        
        evalscript = """//VERSION=3
function setup() {
  return {
    input: ["B02", "B03", "B04", "B08", "B11", "SCL"],
    output: [
      { id: "rgb", bands: 3, sampleType: "AUTO" },
      { id: "indices", bands: 3, sampleType: "AUTO" }
    ]
  };
}
function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
  let ndbi = (sample.B11 - sample.B08) / (sample.B11 + sample.B08 + 0.0001);
  return {
    rgb: [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02],
    indices: [0.5 + ndvi / 2.0, 0.5 + ndbi / 2.0, sample.SCL / 255.0]
  };
}
"""

        payload = {
            "input": {
                "bounds": {
                    "bbox": square_bbox,
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                    }
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": p_from,
                                "to": p_to
                            }
                        }
                    }
                ]
            },
            "output": {
                "width": 256,
                "height": 256,
                "responses": [
                    {
                        "identifier": "rgb",
                        "format": {
                            "type": "image/png"
                        }
                    },
                    {
                        "identifier": "indices",
                        "format": {
                            "type": "image/png"
                        }
                    }
                ]
            },
            "evalscript": evalscript
        }
        
        try:
            # Explicit timeout for Process API
            resp = requests.post(PROCESS_URL, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error or timeout fetching image from Process API: {str(e)}")
        
        if resp.status_code != 200:
            raise RuntimeError(f"Sentinel Hub Process API error: HTTP {resp.status_code} - {resp.text}")
            
        # Extract the images from the TAR archive
        tar = tarfile.open(fileobj=io.BytesIO(resp.content))
        rgb_bytes = tar.extractfile("rgb.png").read()
        indices_bytes = tar.extractfile("indices.png").read()
        
        return rgb_bytes, indices_bytes, cloud_coverage

# Expose a singleton-like helper
_client = None

def get_client():
    global _client
    if _client is None:
        _client = CopernicusClient()
    return _client

def fetch_satellite_image(bbox, date_str):
    return get_client().fetch_satellite_image(bbox, date_str)
