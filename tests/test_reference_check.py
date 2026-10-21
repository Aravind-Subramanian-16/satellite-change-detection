"""Synthetic tests for the reference-map agreement check.

The comparison logic is pure numpy; no downloads, no rasterio, no real
WorldCover data is touched here.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks" / "reference_checks"))

from agreement import (  # noqa: E402
    REPORT_NOTE,
    WORLDCOVER_NAMES,
    build_agreement_report,
    majority_class_in_box,
)

FORBIDDEN = ("accurate", "AI-powered", "state of the art", "reliable", "accuracy")


def _class_map():
    # 40x40 map: water (80) top-left quadrant, built-up (50) elsewhere.
    class_map = np.full((40, 40), 50, dtype=np.uint8)
    class_map[0:20, 0:20] = 80
    return class_map


def test_majority_class_in_box_picks_dominant_class_and_clamps_bounds():
    class_map = _class_map()
    assert majority_class_in_box(class_map, [4, 4, 10, 10]) == 80
    assert majority_class_in_box(class_map, [30, 30, 8, 8]) == 50
    assert majority_class_in_box(class_map, [0, 0, 40, 40]) == 50   # whole map: built-up dominates
    assert majority_class_in_box(class_map, [-5, -5, 4, 4]) is None  # entirely off-map
    assert majority_class_in_box(class_map, [100, 100, 4, 4]) is None


def test_agreement_report_counts_and_skips_honestly():
    regions = [
        {"bounding_box": [5, 5, 8, 8], "change_type": "New surface water"},          # over water -> agrees
        {"bounding_box": [30, 5, 6, 6], "change_type": "New surface water"},         # over built-up -> disagrees
        {"bounding_box": [5, 30, 6, 6], "change_type": "Urban expansion / new construction"},  # over built-up -> agrees
        {"bounding_box": [5, 30, 6, 6], "change_type": "Vegetation gain / reforestation"},     # no expected class
        {"change_type": "Change detected (type unclear)"},                           # no box, no expected class
    ]
    report = build_agreement_report(regions, _class_map(), class_names=WORLDCOVER_NAMES)
    assert report["summary"]["patches_checked"] == 3
    assert report["summary"]["patches_agreeing"] == 2
    assert report["summary"]["patches_skipped_no_expected_class"] == 2
    assert report["summary"]["agreement_percent"] == pytest.approx(66.67)
    assert [row["agrees"] for row in report["rows"]] == [True, False, True]
    assert report["rows"][0]["reference_class_name"] == "water"
    assert report["rows"][1]["reference_class_name"] == "built-up"


def test_agreement_report_never_claims_accuracy():
    lowered = REPORT_NOTE.lower()
    for word in FORBIDDEN:
        assert word not in lowered
    assert "agreement with a reference map" in lowered
    assert "not a performance score" in lowered


def test_agreement_report_with_no_regions_is_empty():
    report = build_agreement_report([], _class_map())
    assert report["rows"] == []
    assert report["summary"]["agreement_percent"] is None
