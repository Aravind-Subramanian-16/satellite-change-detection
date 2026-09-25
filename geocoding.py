import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Identifying the app is required by Nominatim usage policy
USER_AGENT = "satellite-change-detection/1.0"

def geocode_place(place_name: str) -> tuple[str, list[float]]:
    """
    Geocodes a place name using OpenStreetMap's Nominatim API.
    
    Returns:
        A tuple of (resolved_display_name, [min_lon, min_lat, max_lon, max_lat])
        
    Raises:
        ValueError if the place is not found.
        RuntimeError on network or API errors.
    """
    headers = {
        "User-Agent": USER_AGENT
    }
    params = {
        "q": place_name,
        "format": "json",
        "limit": 1
    }
    
    try:
        # Nominatim asks to respect 1 request/sec limit, which is naturally handled 
        # by the interactive nature of this app.
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error querying Nominatim geocoding API: {str(e)}")
        
    if resp.status_code != 200:
        raise RuntimeError(f"Nominatim API error: HTTP {resp.status_code} - {resp.text}")
        
    data = resp.json()
    if not data:
        raise ValueError(f"Could not find a location matching '{place_name}' — try a more specific name or city.")
        
    best_match = data[0]
    display_name = best_match.get("display_name", place_name)
    
    # Nominatim returns boundingbox as [lat_min, lat_max, lon_min, lon_max] (strings)
    bbox_str = best_match.get("boundingbox")
    if not bbox_str or len(bbox_str) != 4:
        raise ValueError(f"Nominatim returned an invalid bounding box for '{place_name}'.")
        
    lat_min, lat_max, lon_min, lon_max = map(float, bbox_str)
    
    # We need to return [lon_min, lat_min, lon_max, lat_max]
    return display_name, [lon_min, lat_min, lon_max, lat_max]

def suggest_places(query: str, limit: int = 5) -> list[dict]:
    """
    Fetches autocomplete suggestions for a place query.
    Returns a list of dicts: [{'display_name', 'lat', 'lon', 'boundingbox'}]
    """
    headers = {
        "User-Agent": USER_AGENT
    }
    params = {
        "q": query,
        "format": "json",
        "limit": limit
    }
    
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error querying Nominatim geocoding API: {str(e)}")
        
    if resp.status_code != 200:
        raise RuntimeError(f"Nominatim API error: HTTP {resp.status_code} - {resp.text}")
        
    results = []
    for item in resp.json():
        bbox_str = item.get("boundingbox")
        if not bbox_str or len(bbox_str) != 4:
            continue
            
        lat_min, lat_max, lon_min, lon_max = map(float, bbox_str)
        # Use our preferred format: [lon_min, lat_min, lon_max, lat_max]
        bbox = [lon_min, lat_min, lon_max, lat_max]
        
        results.append({
            "display_name": item.get("display_name"),
            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "boundingbox": bbox
        })
        
    return results
