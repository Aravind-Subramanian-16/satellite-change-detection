import pytest

from scene_selection import (
    bbox_area_km2,
    coverage_fraction,
    date_window,
    expected_pixels,
    parse_bbox,
    rank_scenes,
    season_warning,
    validate_aoi,
)


def _feature(scene_id, date, cloud, west=0.0, south=0.0, east=0.01, north=0.01):
    return {
        "id": scene_id,
        "properties": {"datetime": f"{date}T10:00:00Z", "eo:cloud_cover": cloud},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
        },
    }


def test_bbox_validation_and_area():
    bbox = parse_bbox("0,0,0.1,0.1")
    assert bbox == [0.0, 0.0, 0.1, 0.1]
    assert 100 < bbox_area_km2(bbox) < 130
    with pytest.raises(ValueError):
        parse_bbox("0,0,1")
    with pytest.raises(ValueError):
        parse_bbox("0,0,-1,1")


def test_aoi_limit_and_pixel_dimensions():
    accepted = validate_aoi([0, 0, 0.05, 0.05], max_km=10)
    assert accepted["valid"]
    assert accepted["expected_pixels"]["analysis_width_px"] >= 64
    rejected = validate_aoi([0, 0, 0.2, 0.2], max_km=10)
    assert not rejected["valid"]
    assert "limit is 10 km" in rejected["message"]


def test_expected_pixels_are_capped():
    pixels = expected_pixels([0, 0, 0.09, 0.09], max_px=512)
    assert pixels["analysis_width_px"] <= 512
    assert pixels["capped"] is True


def test_coverage_uses_footprint_intersection():
    bbox = [0, 0, 0.01, 0.01]
    assert coverage_fraction(_feature("full", "2024-01-01", 10), bbox) == pytest.approx(1.0)
    half = _feature("half", "2024-01-01", 10, west=0.005, east=0.015)
    assert 0.4 < coverage_fraction(half, bbox) < 0.6


def test_ranking_prefers_clear_close_complete_scene():
    bbox = [0, 0, 0.01, 0.01]
    features = [
        _feature("cloudy-close", "2024-06-10", 80),
        _feature("clear-far", "2024-06-01", 5),
        _feature("clear-close", "2024-06-11", 3),
        _feature("clear-close-partial", "2024-06-11", 0, west=0.009, east=0.02),
    ]
    ranked = rank_scenes(features, bbox, "2024-06-10", window_days=30, top=3)
    assert ranked[0]["id"] == "clear-close"
    assert ranked[0]["recommended"] is True
    assert [row["rank"] for row in ranked] == [1, 2, 3]
    assert ranked[0]["coverage_percent"] > 99


def test_season_warning():
    assert season_warning("2024-01-10", "2024-02-10") is None
    warning = season_warning("2024-02-10", "2024-06-10")
    assert warning and "season" in warning.lower()


def test_date_window_is_inclusive_and_symmetric():
    start, end = date_window("2024-06-10", 30)
    assert start == "2024-05-11T00:00:00Z"
    assert end == "2024-07-10T23:59:59Z"
