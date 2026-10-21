"""Network-free tests for the live-analysis HTTP contract.

Every test replaces ``copernicus_client.get_client`` with an in-memory fake,
so nothing here can authenticate, query a catalog or download imagery.
"""
from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as app_module
import history_store
import security
from copernicus_client import MissingCredentialsError
from spectral_pipeline import encode_indices

BBOX = [10.0, 20.0, 10.01, 20.005]
BEFORE = "2024-01-05"
AFTER = "2024-02-05"


def _scene_id(date_str: str, role: str) -> str:
    return f"S2_{date_str}_{role}"


def _png(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(np.asarray(array, dtype=np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def _encoded_ext(nbr: np.ndarray, ndmi: np.ndarray, bsi: np.ndarray) -> np.ndarray:
    return np.dstack(
        [
            (np.clip(nbr, -1, 1) / 2.0 + 0.5) * 255.0,
            (np.clip(ndmi, -1, 1) / 2.0 + 0.5) * 255.0,
            (np.clip(bsi, -1, 1) / 2.0 + 0.5) * 255.0,
        ]
    ).astype(np.uint8)


class FakeCopernicusClient:
    """Three fixed catalog candidates per window and deterministic PNG bundles."""

    def __init__(
        self,
        before_date: str = BEFORE,
        after_date: str = AFTER,
        *,
        empty: bool = False,
        search_error: Exception | None = None,
        coverage: str = "full",
    ):
        self.before_date = before_date
        self.after_date = after_date
        self.empty = empty
        self.search_error = search_error
        self.coverage = coverage
        self.search_calls: list[tuple[str, int]] = []
        self.fetch_calls: list[str] = []

    def _geometry(self, bbox: list[float]) -> dict:
        min_lon, min_lat, max_lon, max_lat = bbox
        if self.coverage == "half":
            max_lon = (min_lon + max_lon) / 2.0
        ring = [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]
        return {"type": "Polygon", "coordinates": [ring]}

    def search_scenes(self, bbox, date_str: str, window_days: int = 30, limit: int = 50):
        self.search_calls.append((str(date_str), int(window_days)))
        if self.search_error is not None:
            raise self.search_error
        if self.empty:
            return []
        when = f"{str(date_str)[:10]}T10:00:00Z"
        geometry = self._geometry(list(bbox))
        return [
            {
                "id": _scene_id(str(date_str)[:10], role),
                "properties": {"datetime": when, "eo:cloud_cover": cloud},
                "geometry": geometry,
            }
            for role, cloud in (("CLEAR", 2.0), ("PARTLY", 70.0), ("MASKED", 100.0))
        ]

    def fetch_scene(self, bbox, scene: dict, output_size: tuple[int, int] | None = None) -> dict:
        width, height = output_size or (64, 64)
        scene_id = str(scene["id"])
        self.fetch_calls.append(scene_id)
        scene_date = str((scene.get("properties") or {}).get("datetime", ""))[:10]
        after = scene_date >= self.after_date
        role = scene_id.rsplit("_", 1)[-1]

        shape = (int(height), int(width))
        ndvi = np.full(shape, 0.62, dtype=np.float32)
        ndbi = np.zeros(shape, dtype=np.float32)
        nbr = np.full(shape, 0.50, dtype=np.float32)
        ndmi = np.full(shape, 0.45, dtype=np.float32)
        bsi = np.full(shape, 0.10, dtype=np.float32)
        rgb = np.full(shape + (3,), 70 if not after else 90, dtype=np.uint8)

        if after:
            rows = slice(shape[0] // 3, (2 * shape[0]) // 3)
            cols = slice(shape[1] // 3, (2 * shape[1]) // 3)
            ndvi[rows, cols] = 0.15
            ndbi[rows, cols] = 0.35
            nbr[rows, cols] = 0.20
            ndmi[rows, cols] = 0.20
            bsi[rows, cols] = 0.30
            rgb[rows, cols] = (130, 125, 120)

        scl = np.zeros(shape, dtype=np.uint8)
        if role == "PARTLY":
            scl[:, : max(1, shape[1] // 2)] = 9
        elif role == "MASKED":
            scl[:] = 9

        return {
            "rgb": _png(rgb),
            "indices": _png(encode_indices(ndvi, ndbi, scl)),
            "indices_ext": _png(_encoded_ext(nbr, ndmi, bsi)),
            "cloud_cover": (scene.get("properties") or {}).get("eo:cloud_cover"),
            "scene_id": scene_id,
            "datetime": (scene.get("properties") or {}).get("datetime"),
            "bbox": list(bbox),
            "width": int(width),
            "height": int(height),
        }


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(history_store, "DB_PATH", tmp_path / "history.sqlite3")
    return TestClient(app_module.app)


def _use_fake(monkeypatch, fake: FakeCopernicusClient) -> FakeCopernicusClient:
    monkeypatch.setattr(app_module.copernicus, "get_client", lambda: fake)
    return fake


def _scenes_payload(date_before: str = BEFORE, date_after: str = AFTER) -> dict:
    return {"bbox": BBOX, "date_before": date_before, "date_after": date_after, "window_days": 30}


def _live_payload(**overrides) -> dict:
    payload = {
        "bbox": BBOX,
        "date_before": BEFORE,
        "date_after": AFTER,
        "window_days": 30,
        "profile": "general",
    }
    payload.update(overrides)
    return payload


def test_scenes_returns_ranked_windows_and_recommendation(client, monkeypatch):
    fake = _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/scenes", json=_scenes_payload())

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["before"]["recommended_id"] == _scene_id(BEFORE, "CLEAR")
    assert data["after"]["recommended_id"] == _scene_id(AFTER, "CLEAR")
    scores = [row["score"] for row in data["before"]["scenes"]]
    assert scores == sorted(scores, reverse=True)
    assert data["before"]["scenes"][0]["recommended"] is True
    assert data["before"]["start"].startswith("2023-12-06")
    assert data["aoi"]["valid"] is True
    assert data["warnings"] == []
    assert fake.search_calls == [(BEFORE, 30), (AFTER, 30)]


def test_scenes_warns_on_partial_coverage_and_cross_season(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient(coverage="half"))
    response = client.post("/scenes", json=_scenes_payload("2024-01-05", "2024-07-05"))

    assert response.status_code == 200, response.text
    data = response.json()
    codes = [warning["code"] for warning in data["warnings"]]
    assert codes.count("coverage") == 2
    assert "season" in codes
    assert data["before"]["scenes"][0]["coverage_percent"] == 50.0
    season = next(w for w in data["warnings"] if w["code"] == "season")
    assert "Dec–Feb" in season["message"]
    assert "Jun–Aug" in season["message"]


def test_scenes_rejects_oversized_aoi_without_network(client, monkeypatch):
    fake = _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/scenes", json={**_scenes_payload(), "bbox": [10.0, 20.0, 10.2, 20.005]})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "limit is 10 km" in response.json()["error"]
    assert fake.search_calls == []


def test_scenes_rejects_bad_dates(client):
    response = client.post("/scenes", json=_scenes_payload("not-a-date", AFTER))
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_scenes_maps_missing_credentials(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient(search_error=MissingCredentialsError("no credentials")))
    response = client.post("/scenes", json=_scenes_payload())

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "missing_credentials"
    assert "COPERNICUS_CLIENT_ID" in body["hint"]


def test_scenes_returns_404_when_catalog_is_empty(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient(empty=True))
    response = client.post("/scenes", json=_scenes_payload())

    assert response.status_code == 404
    assert response.json()["code"] == "no_scenes"


def test_fetch_and_predict_returns_analysis_and_persists_history(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload())

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["pipeline"] == "spectral"
    assert data["profile"] == "general"
    assert data["scenes"]["before"]["id"] == _scene_id(BEFORE, "CLEAR")
    assert data["scenes"]["after"]["id"] == _scene_id(AFTER, "CLEAR")
    assert 0 < data["percent_changed"] < 100
    assert data["percent_cloud_masked"] == 0.0
    assert data["change_regions"]
    assert data["display_metrics"] is False
    assert data["validation_status"].startswith("unvalidated")
    assert data["provenance"]["scene_ids"] == [
        _scene_id(BEFORE, "CLEAR"),
        _scene_id(AFTER, "CLEAR"),
    ]
    history_id = data["history_id"]
    assert isinstance(history_id, int) and history_id > 0

    stored = client.get(f"/history/{history_id}")
    assert stored.status_code == 200
    assert stored.json()["result"]["percent_changed"] == pytest.approx(data["percent_changed"])
    exported = client.get(f"/history/{history_id}/export/geojson")
    assert exported.status_code == 200
    assert exported.json()["type"] == "FeatureCollection"


def test_fetch_and_predict_honours_selected_scene_and_warns_on_cloud(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    selected_after = _scene_id(AFTER, "PARTLY")
    response = client.post("/fetch-and-predict", json=_live_payload(scene_after_id=selected_after))

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["scenes"]["after"]["id"] == selected_after
    cloud_warnings = [warning for warning in data["warnings"] if warning["code"] == "cloud"]
    assert len(cloud_warnings) == 1
    assert cloud_warnings[0]["window"] == "after"
    assert "classes 3, 8, 9, 10" in cloud_warnings[0]["message"]
    assert 40 <= data["aoi_cloud_fraction_after"] <= 60


def test_fetch_and_predict_rejects_unknown_selected_scene(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload(scene_after_id="not-in-window"))

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "is not in the" in response.json()["error"]


def test_fetch_and_predict_returns_422_details_when_scene_is_fully_masked(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post(
        "/fetch-and-predict",
        json=_live_payload(scene_after_id=_scene_id(AFTER, "MASKED")),
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "fully_masked"
    details = body["details"]
    assert details["window"] == "after"
    assert details["cloud_fraction_percent"] >= 99.5
    assert details["candidates"]
    assert "another scene" in details["suggestion"]


def test_fetch_and_predict_supports_builtup_extended_indices(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload(profile="builtup"))

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["profile"] == "builtup"
    assert data["display_metrics"] is True
    assert "OSCD" in data["validation_status"]
    assert data["change_regions"]


def test_fetch_and_predict_water_profile_reports_honest_plumbing(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload(profile="water"))

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["profile"] == "water"
    assert data["validation_status"] == "unvalidated, qualitative only"
    assert data["display_metrics"] is False
    provenance = data["provenance"]["threshold_provenance"]
    assert provenance["water_ndvi_max"].startswith("chosen by developer, untested")
    assert data["class_table"] == {"rows": [], "total": {
        "change_type": "Total", "area_ha": 0.0, "area_m2": 0.0,
        "percent_of_aoi": 0.0, "region_count": 0,
    }, "note": data["class_table"]["note"]}


def test_fetch_and_predict_agriculture_adds_crop_cycle_note_and_explanations(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload(profile="agriculture"))

    assert response.status_code == 200, response.text
    data = response.json()
    codes = [warning["code"] for warning in data["warnings"]]
    assert "crop_cycle" in codes
    assert data["change_regions"]
    assert all(region["explanation"] for region in data["change_regions"])
    assert data["class_table"]["rows"]
    assert data["class_table"]["total"]["region_count"] == len(data["change_regions"])


def test_exported_class_table_matches_the_api_response(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload(profile="agriculture"))
    data = response.json()

    geojson = client.post("/export/geojson", json={"result": data})
    assert geojson.status_code == 200
    assert geojson.json()["metadata"]["class_table"]["rows"] == data["class_table"]["rows"]

    csv = client.post("/export/csv", json={"result": data})
    assert csv.status_code == 200
    assert "\nclass_summary\n" in csv.text
    block = [line for line in csv.text.split("class_summary\n", 1)[1].strip().splitlines() if not line.startswith("#")]
    header = block[0].split(",")
    total = block[-1].split(",")
    assert header[:2] == ["class", "area_ha"]
    assert total[0] == "Total"
    assert float(total[1]) == pytest.approx(data["class_table"]["total"]["area_ha"])


def _pdf_text(data: bytes) -> str:
    import base64
    import re
    import zlib

    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.DOTALL):
        raw = match.group(1).strip()
        try:
            if raw.endswith(b"~>"):
                raw = base64.a85decode(raw, adobe=True)
            raw = zlib.decompress(raw)
        except Exception:  # noqa: BLE001, S112 - image streams use filters we do not decode
            continue
        chunks.append(raw.decode("latin-1", "replace"))
    return "\n".join(chunks)


def test_report_endpoint_returns_pdf_with_the_same_numbers(client, monkeypatch):
    pytest.importorskip("reportlab")
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload(profile="agriculture"))
    data = response.json()

    report = client.post("/report", json={"result": data})
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")
    text = _pdf_text(report.content)
    assert "Summary in plain language" in text
    assert f"{data['percent_changed']:.2f}%" in text
    for row in data["class_table"]["rows"]:
        assert f"{float(row['area_ha']):.2f}" in text
        assert f"{float(row['percent_of_aoi']):.2f}%" in text

    empty = client.post("/report", json={"result": {}})
    assert empty.status_code == 200
    assert empty.content.startswith(b"%PDF")


def test_history_report_endpoint_returns_the_stored_pdf(client, monkeypatch):
    pytest.importorskip("reportlab")
    _use_fake(monkeypatch, FakeCopernicusClient())
    data = client.post("/fetch-and-predict", json=_live_payload()).json()

    report = client.get(f"/history/{data['history_id']}/report")
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")

    missing = client.get("/history/999999/report")
    assert missing.status_code == 404


def test_history_routes_are_rate_limited():
    assert security.is_rate_limited_path("/history")
    assert security.is_rate_limited_path("/history/12/report")
    assert security.is_rate_limited_path("/history/12/export/geojson")


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"mmu_ha": 101}, "mmu_ha"),
        ({"composite_scenes": 4}, "composite_scenes"),
        ({"profile": "not-a-profile"}, "Unknown analysis profile"),
    ],
)
def test_fetch_and_predict_validates_options_before_network(client, monkeypatch, overrides, fragment):
    fake = _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post("/fetch-and-predict", json=_live_payload(**overrides))

    assert response.status_code == 400
    assert fragment in response.json()["error"]
    assert fake.search_calls == []


def test_timeline_returns_masked_ndvi_points(client, monkeypatch):
    _use_fake(monkeypatch, FakeCopernicusClient())
    response = client.post(
        "/timeline",
        json={"bbox": BBOX, "dates": [BEFORE, AFTER, "2024-03-05"], "window_days": 10},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["profile"] == "agriculture"
    assert len(data["points"]) == 3
    assert all(point["ndvi_mean"] is not None for point in data["points"])
    assert all(0 <= point["valid_percent"] <= 100 for point in data["points"])
    assert "Unvalidated" in data["note"]


def test_timeline_rejects_wrong_date_count_and_duplicates(client, monkeypatch):
    fake = _use_fake(monkeypatch, FakeCopernicusClient())
    two_dates = client.post("/timeline", json={"bbox": BBOX, "dates": [BEFORE, AFTER]})
    assert two_dates.status_code == 400
    assert "3 to 5 dates" in two_dates.json()["error"]

    duplicates = client.post(
        "/timeline",
        json={"bbox": BBOX, "dates": [BEFORE, BEFORE, AFTER]},
    )
    assert duplicates.status_code == 400
    assert "unique" in duplicates.json()["error"]
    assert fake.search_calls == []


def test_export_and_report_endpoints(client):
    result = {
        "pipeline": "spectral",
        "aoi": {"bbox": BBOX},
        "provenance": {"commit": "abc"},
        "change_regions": [
            {
                "bounding_box": [10, 20, 30, 40],
                "pixel_area": 1200,
                "change_type": "Urban expansion / new construction",
                "confidence_label": "High",
                "area_ha": 12.0,
            }
        ],
    }
    geojson = client.post("/export/geojson", json={"result": result})
    assert geojson.status_code == 200
    assert geojson.headers["content-type"].startswith("application/geo+json")
    assert geojson.json()["features"][0]["properties"]["area_ha"] == 12.0

    csv = client.post("/export/csv", json={"result": result})
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[0].startswith("region_id,change_type")

    assert client.post("/export/pdf", json={"result": result}).status_code == 404

    report = client.post("/report", json={"result": {"percent_changed": 1.0, "change_regions": []}})
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")


def test_export_requires_result_object(client):
    response = client.post("/export/geojson", json={"result": "not-an-object"})
    assert response.status_code == 422
