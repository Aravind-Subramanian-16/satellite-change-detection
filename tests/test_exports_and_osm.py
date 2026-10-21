import json
from pathlib import Path

import numpy as np
import pytest

import osm_roads
from exports import regions_to_csv, regions_to_geojson
from osm_roads import fetch_roads, road_context_from_elements


def _result():
    return {
        "pipeline": "spectral",
        "profile": "builtup",
        "validation_status": "quantitatively benchmarked on OSCD (urban change only, pooled F1 about 0.12)",
        "percent_cloud_masked": 4.0,
        "image_shape": [100, 200],
        "aoi": {"bbox": [10.0, 20.0, 10.01, 20.005]},
        "provenance": {"commit": "abc", "scene_ids": ["s1"], "dates": {"before": "2024-01-01"}, "timestamp_utc": "2024-01-01T00:00:00+00:00"},
        "change_regions": [
            {"bounding_box": [10, 20, 30, 40], "pixel_area": 1200, "change_type": "Urban expansion / new construction", "confidence_label": "High", "area_ha": 12.0, "uncertainty": 0.8},
        ],
    }


def test_geojson_has_geographic_polygon_and_provenance():
    data = regions_to_geojson(_result())
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    feature = data["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    ring = feature["geometry"]["coordinates"][0]
    assert 10.0 <= ring[0][0] <= 10.01
    assert 20.0 <= ring[0][1] <= 20.005
    assert feature["properties"]["area_ha"] == 12.0
    assert data["metadata"]["coordinate_reference_system"] == "EPSG:4326"
    assert data["metadata"]["commit"] == "abc"


def test_geojson_without_aoi_is_pixel_referenced():
    result = {"change_regions": [{"bounding_box": [0, 0, 5, 5], "pixel_area": 25, "change_type": "x", "confidence_label": "Low"}]}
    data = regions_to_geojson(result)
    assert data["metadata"]["coordinate_reference_system"].startswith("image-pixel")


def test_csv_has_header_and_rows():
    text = regions_to_csv(_result())
    lines = text.strip().splitlines()
    assert lines[0].startswith("region_id,change_type")
    assert "Urban expansion" in lines[1]
    assert len(lines) == 2


def _overpass_payload():
    return {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"highway": "primary"},
                "geometry": [
                    {"lat": 20.0025, "lon": 10.0},
                    {"lat": 20.0025, "lon": 10.01},
                ],
            }
        ]
    }


def test_fetch_roads_caches_without_second_network_call(tmp_path, monkeypatch):
    calls = {"count": 0}

    class Response:
        status_code = 200

        def json(self):
            return _overpass_payload()

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return Response()

    monkeypatch.setattr(osm_roads.requests, "post", fake_post)
    first = fetch_roads([10.0, 20.0, 10.01, 20.005], cache_dir=tmp_path)
    assert first["cached"] is False
    assert len(first["roads"]) == 1
    monkeypatch.setattr(osm_roads.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    second = fetch_roads([10.0, 20.0, 10.01, 20.005], cache_dir=tmp_path)
    assert second["cached"] is True
    assert calls["count"] == 1


def test_road_context_reports_only_nearby_changed_pixels():
    bbox = [10.0, 20.0, 10.01, 20.005]
    roads = [{"id": 1, "highway": "primary", "points": [[10.0, 20.0025], [10.01, 20.0025]]}]
    mask = np.zeros((100, 200), np.uint8)
    mask[49:51, :] = 1        # on the road
    mask[0:2, :] = 1          # far from the road (~500 m)
    result = road_context_from_elements(mask, bbox, roads, distance_m=50)
    assert result["total_changed_pixels"] == 800
    assert result["changed_pixels_near_roads"] == 400
    assert result["percent_changed_within_distance"] == 50.0
    assert "not road detection" in result["note"]
    assert "OpenStreetMap" in result["attribution"]
