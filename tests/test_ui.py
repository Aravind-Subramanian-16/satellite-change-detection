"""Browser-level checks for the redesigned UI (Phase 1).

These tests drive the real page with Playwright against a live uvicorn
instance, mocking the Copernicus-dependent routes so they stay offline.
They are skipped when Playwright or Google Chrome is unavailable.
"""
import base64
import io
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if not os.path.exists(CHROME):  # pragma: no cover
    pytest.skip("Google Chrome not found; UI tests need a browser", allow_module_level=True)

PORT = 8029
BASE = f"http://127.0.0.1:{PORT}"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _png_b64(colour):
    if Image is None:  # pragma: no cover
        return ""
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100), colour).save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode()


SCENES_FIXTURE = {
    "before": {
        "requested_date": "2023-01-15",
        "start": "2022-12-16T00:00:00Z",
        "end": "2023-02-13T23:59:59Z",
        "recommended_id": "S2A_before",
        "scenes": [
            {"id": "S2A_before", "date": "2023-01-16", "cloud_cover_percent": 3.2, "coverage_percent": 99.9, "score": 0.96, "days_from_target": 1, "rank": 1, "recommended": True},
        ],
    },
    "after": {
        "requested_date": "2023-07-15",
        "start": "2023-06-15T00:00:00Z",
        "end": "2023-08-14T23:59:59Z",
        "recommended_id": "S2B_after",
        "scenes": [
            {"id": "S2B_after", "date": "2023-07-18", "cloud_cover_percent": 12.0, "coverage_percent": 98.5, "score": 0.9, "days_from_target": 3, "rank": 1, "recommended": True},
        ],
    },
    "season_warning": "Before is in Dec–Feb while after is in Jun–Aug.",
    "warnings": [],
}


def _result_fixture():
    return {
        "pipeline": "spectral",
        "profile": "general",
        "profile_label": "General",
        "percent_changed": 3.21,
        "percent_changed_valid": 4.05,
        "percent_cloud_masked": 2.5,
        "image_shape": [100, 100],
        "aoi": {"bbox": [55.1302, 25.1005, 55.1524, 25.1174], "area_km2": 4.92,
                "expected_pixels": {"pixel_size_x_m": 10.0, "pixel_size_y_m": 10.0}},
        "warnings": [{"severity": "high", "message": "One image is 40 days from its target date."}],
        "season_warning": "Before is in Dec–Feb while after is in Jun–Aug.",
        "cloud_coverage_before": 4.0,
        "cloud_coverage_after": 38.0,
        "aoi_cloud_fraction_before": 0.02,
        "aoi_cloud_fraction_after": 0.35,
        "summary_sentence": "About 3.2% of the area changed between the two dates.",
        "scenes": {
            "before": {"date": "2023-01-16T00:00:00Z", "requested_date": "2023-01-15"},
            "after": {"date": "2023-07-18T00:00:00Z", "requested_date": "2023-07-15"},
        },
        "change_regions": [
            {"bounding_box": [10, 20, 30, 40], "pixel_area": 320, "area_ha": 0.32,
             "change_type": "Urban expansion / new construction", "confidence_label": "Medium",
             "explanation": "The built-up index rose while vegetation fell, and the patch looks uniform and grey in the after image.",
             "stats": {"veg_ratio_before": 0.4, "veg_ratio_after": 0.1}},
            {"bounding_box": [50, 60, 10, 10], "pixel_area": 90, "area_ha": 0.09,
             "change_type": "Vegetation gain / reforestation", "confidence_label": "Low", "stats": {}},
        ],
        "class_table": {
            "rows": [
                {"change_type": "Urban expansion / new construction", "area_ha": 0.32, "area_m2": 3200.0,
                 "percent_of_aoi": 0.065, "region_count": 1},
                {"change_type": "Vegetation gain / reforestation", "area_ha": 0.09, "area_m2": 900.0,
                 "percent_of_aoi": 0.018, "region_count": 1},
            ],
            "total": {"change_type": "Total", "area_ha": 0.41, "area_m2": 4100.0,
                      "percent_of_aoi": 0.083, "region_count": 2},
            "note": "Area per type is summed over the patches shown.",
        },
        "validation_status": "This profile has not been tested on labelled data.",
        "display_metrics": False,
        "image_a": _png_b64((40, 70, 40)),
        "image_b": _png_b64((120, 100, 60)),
        "mask_base64": _png_b64((255, 255, 255)),
        "overlay_base64": _png_b64((200, 60, 60)),
        "confidence_base64": None,
        "provenance": {"commit": "abc1234", "scene_ids": ["S2A_before", "S2B_after"],
                       "timestamp_utc": "2026-10-21T00:00:00+00:00"},
        "profile_notes": ["Note one.", "Note two."],
        "road_context": None,
        "history_id": 123,
        "thresholds": {},
    }


HISTORY_FIXTURE = [
    {"id": 5, "created_at": "2026-10-21T12:00:00+00:00", "location": "Example delta", "pipeline": "spectral", "percent_changed": 12.5},
    {"id": 4, "created_at": "2026-10-20T12:00:00+00:00", "location": "Example forest", "pipeline": "spectral", "percent_changed": 7.5},
    {"id": 3, "created_at": "2026-10-19T12:00:00+00:00", "location": "Example town", "pipeline": "spectral", "percent_changed": 3.0},
    {"id": 2, "created_at": "2026-10-18T12:00:00+00:00", "location": "Example fields", "pipeline": "cnn", "percent_changed": 0.4},
    {"id": 1, "created_at": "2026-10-17T12:00:00+00:00", "location": "Example coast", "pipeline": "spectral", "percent_changed": 0.0},
]


@pytest.fixture(scope="module")
def server():
    repo = Path(__file__).resolve().parent.parent
    proc = subprocess.Popen(
        [str(repo / "venv/bin/python"), "-m", "uvicorn", "app:app", "--port", str(PORT), "--log-level", "error"],
        cwd=str(repo),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                break
        except OSError:
            time.sleep(0.2)
    yield BASE
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture()
def page(server):
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        pg = context.new_page()
        pg.route("**/scenes", lambda route: route.fulfill(json=SCENES_FIXTURE))
        pg.route("**/fetch-and-predict", lambda route: route.fulfill(json=_result_fixture()))
        yield pg
        browser.close()


def test_wizard_flow_goal_sync_and_area_formatting(page):
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(500)
    if page.locator("#hint-tour").is_visible():
        page.click("#hint-skip")

    assert page.locator("#step-1").is_visible()
    assert not page.locator("#step-2").is_visible()
    assert page.locator("#to-dates-btn").is_disabled()
    assert page.locator("#honesty-note").is_visible()

    page.locator(".manual-aoi summary").click()
    page.fill("#aoi-manual", "55.1310, 25.1070, 55.1315, 25.1075")
    page.click("#apply-bbox-btn")
    page.wait_for_timeout(300)
    status = page.locator("#aoi-status").inner_text()
    assert "km²" not in status  # never "0.00 km²" for small areas
    assert "ha" in status or "m²" in status
    assert "Very small area" in page.locator("#aoi-info").inner_text()
    assert page.locator("#to-dates-btn").is_enabled()

    page.click("#to-dates-btn")
    page.wait_for_timeout(300)
    assert page.locator("#step-2").is_visible()

    page.locator(".goal-card", has_text="Farmland changes").click()
    assert page.locator("#profile-select").input_value() == "agriculture"
    assert "crop" in page.locator("#goal-note").inner_text().lower()
    page.locator(".goal-card", has_text="Water changes").click()
    assert page.locator("#profile-select").input_value() == "water"
    assert "moisture" in page.locator("#goal-note").inner_text().lower()


def test_theme_toggle_and_friendly_network_error(page):
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(500)
    if page.locator("#hint-tour").is_visible():
        page.click("#hint-skip")

    initial = page.get_attribute("html", "data-theme")
    page.click("#theme-toggle")
    page.wait_for_timeout(200)
    toggled = page.get_attribute("html", "data-theme")
    assert toggled in ("light", "dark") and toggled != initial
    page.click("#theme-toggle")
    assert page.get_attribute("html", "data-theme") == initial

    page.unroute("**/scenes")
    page.route("**/scenes", lambda route: route.abort())
    page.locator(".manual-aoi summary").click()
    page.fill("#aoi-manual", "55.1310, 25.1070, 55.1320, 25.1080")
    page.click("#apply-bbox-btn")
    page.click("#to-dates-btn")
    page.wait_for_timeout(300)
    page.click("#find-scenes-btn")
    page.wait_for_timeout(600)
    error = page.locator("#live-error").inner_text()
    assert "could not reach the analysis service" in error


def test_results_dashboard_and_mobile_layout(page):
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(500)
    if page.locator("#hint-tour").is_visible():
        page.click("#hint-skip")

    page.click("#load-example-btn")
    page.wait_for_timeout(500)
    assert page.locator("#step-2").is_visible()
    assert page.locator("#date-before").input_value() == "2023-01-15"
    assert page.locator("#date-after").input_value() == "2023-07-15"

    page.click("#find-scenes-btn")
    page.wait_for_timeout(500)
    assert page.locator("#scene-section").is_visible()
    assert page.locator("#run-analysis-btn").is_enabled()

    page.click("#run-analysis-btn")
    page.wait_for_timeout(800)
    assert page.locator("#results-section").is_visible()
    assert page.get_attribute('.wizard-progress li[data-step="3"]', "aria-current") == "step"
    assert page.locator("#quality-badge").is_visible()
    assert page.locator(".summary-card").count() == 3
    cards = page.locator("#summary-cards").inner_text().lower()
    assert "area changed" in cards and "share of the area" in cards and "main change type" in cards
    assert "0.00 km²" not in cards
    assert "2 patches" in page.locator("#region-count").inner_text()
    assert page.locator("#download-heading").inner_text() == "Download the results"

    assert page.locator("#class-table-block").is_visible()
    table_text = page.locator("#class-table-body").inner_text()
    assert "Urban expansion / new construction" in table_text
    assert "Vegetation gain" in table_text
    assert "Total" in table_text
    assert "m²" in table_text or "ha" in table_text  # small class areas never shown as 0.00 km²
    assert "km²" not in table_text
    page.locator(".region-why summary").first.click()
    assert "built-up index" in page.locator(".region-why p").first.inner_text()

    page.set_viewport_size({"width": 375, "height": 812})
    page.wait_for_timeout(300)
    page.click("#new-analysis-btn")
    page.wait_for_timeout(300)
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1, f"horizontal overflow {overflow}px"

    page.click("#back-to-area-btn")
    page.wait_for_timeout(300)
    assert page.locator("#step-1").is_visible()
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1, f"horizontal overflow {overflow}px"


def test_history_dashboard_aggregates_rows_and_hides_when_empty(page):
    page.route("**/history", lambda route: route.fulfill(json=HISTORY_FIXTURE))
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(500)
    if page.locator("#hint-tour").is_visible():
        page.click("#hint-skip")

    page.click("#tab-history")
    page.wait_for_timeout(400)
    dashboard = page.locator("#history-dashboard")
    assert dashboard.is_visible()
    assert not page.locator(".intro").is_visible()  # dashboard is the focus of this view
    stats = page.locator("#history-stats").inner_text()
    stats_lower = stats.lower()
    assert "saved analyses" in stats_lower and "5" in stats
    assert "4 / 1" in stats  # four live analyses, one image pair
    assert "4.68%" in stats  # simple mean of 12.5, 7.5, 3.0, 0.4, 0.0
    assert "12.50%" in stats
    assert "not area-weighted" in stats_lower

    recent = page.locator("#history-recent-chart")
    assert recent.locator(".chart-row").count() == 5
    assert "#5" in recent.inner_text() and "Example delta" in recent.inner_text()
    ranges = page.locator("#history-range-chart").inner_text()
    assert "Under 1%" in ranges and "2 analyses" in ranges
    assert "10% or more" in ranges and "1 analysis" in ranges

    page.set_viewport_size({"width": 375, "height": 812})
    page.wait_for_timeout(300)
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1, f"horizontal overflow {overflow}px"
    history_tab = page.locator("#tab-history").bounding_box()
    assert history_tab and history_tab["x"] + history_tab["width"] <= 375

    page.unroute("**/history")
    page.route("**/history", lambda route: route.fulfill(json=[]))
    page.click("#refresh-history-btn")
    page.wait_for_timeout(400)
    assert not dashboard.is_visible()
    assert "No analyses yet" in page.locator("#history-list").inner_text()

    page.click("#tab-live")
    page.wait_for_timeout(300)
    assert page.locator(".intro").is_visible()
