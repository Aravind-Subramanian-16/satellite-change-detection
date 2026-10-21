"""Robustness tests: Copernicus retries, bounded scene cache and /health.

Everything here is network-free; requests.post is replaced with in-memory
fakes and no credentials are real.
"""
from __future__ import annotations

import io
import tarfile

import pytest
import requests
from fastapi.testclient import TestClient

import app as app_module
import copernicus_client as cc


class FakeResponse:
    def __init__(self, status_code=200, content=b"", payload=None, headers=None, text=""):
        self.status_code = status_code
        self.content = content
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


def _tar_bytes() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, payload in (
            ("rgb.png", b"rgb-bytes"),
            ("indices.png", b"indices-bytes"),
            ("indices_ext.png", b"ext-bytes"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def _scene(scene_id="S2A_TEST"):
    return {
        "id": scene_id,
        "datetime": "2025-05-01T10:00:00Z",
        "properties": {"eo:cloud_cover": 4.2},
    }


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch):
    monkeypatch.setattr(cc, "RETRY_BASE_SECONDS", 0.0)


# ── Retries ──────────────────────────────────────────────────────────────────


def test_post_with_retry_retries_transient_status_then_succeeds(monkeypatch):
    monkeypatch.setattr(cc, "RETRY_BASE_SECONDS", 1.0)
    responses = [FakeResponse(503), FakeResponse(200, payload={"ok": True})]
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return responses.pop(0)

    monkeypatch.setattr(cc.requests, "post", fake_post)
    delays = []
    response = cc._post_with_retry("http://example", sleep_fn=delays.append)
    assert response.status_code == 200
    assert len(calls) == 2
    assert len(delays) == 1


def test_post_with_retry_stops_after_attempt_limit(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return FakeResponse(502)

    monkeypatch.setattr(cc.requests, "post", fake_post)
    response = cc._post_with_retry("http://example", sleep_fn=lambda _: None, attempts=3)
    assert response.status_code == 502
    assert len(calls) == 3


def test_post_with_retry_does_not_retry_client_errors(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return FakeResponse(401)

    monkeypatch.setattr(cc.requests, "post", fake_post)
    response = cc._post_with_retry("http://example", sleep_fn=lambda _: None)
    assert response.status_code == 401
    assert len(calls) == 1


def test_post_with_retry_reraises_network_errors_after_limit(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(cc.requests, "post", fake_post)
    with pytest.raises(requests.ConnectionError):
        cc._post_with_retry("http://example", sleep_fn=lambda _: None, attempts=2)
    assert len(calls) == 2


def test_post_with_retry_honours_retry_after_header(monkeypatch):
    responses = [FakeResponse(429, headers={"Retry-After": "2"}), FakeResponse(200)]
    monkeypatch.setattr(cc.requests, "post", lambda url, **kwargs: responses.pop(0))
    delays = []
    cc._post_with_retry("http://example", sleep_fn=delays.append)
    assert delays == [2.0]


def test_token_request_is_retried_then_cached(monkeypatch):
    monkeypatch.setenv("COPERNICUS_CLIENT_ID", "id-value")
    monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "secret-value")
    responses = [
        FakeResponse(503),
        FakeResponse(200, payload={"access_token": "token-1", "expires_in": 3600}),
    ]
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return responses.pop(0)

    monkeypatch.setattr(cc.requests, "post", fake_post)
    client = cc.CopernicusClient()
    assert client._get_token() == "token-1"
    assert client._get_token() == "token-1"
    assert len(calls) == 2


def test_catalog_search_retries_transient_failure(monkeypatch):
    monkeypatch.setenv("COPERNICUS_CLIENT_ID", "id-value")
    monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "secret-value")
    features = [{"id": "S2A_TEST", "datetime": "2025-05-01T10:00:00Z", "properties": {}}]
    responses = [
        FakeResponse(200, payload={"access_token": "token-1", "expires_in": 3600}),
        FakeResponse(502),
        FakeResponse(200, payload={"features": features}),
    ]
    monkeypatch.setattr(cc.requests, "post", lambda url, **kwargs: responses.pop(0))
    client = cc.CopernicusClient()
    assert client.search_scenes([10.0, 20.0, 10.01, 20.01], "2025-05-01", window_days=5) == features


# ── Scene cache ──────────────────────────────────────────────────────────────


def test_fetch_scene_second_call_is_served_from_cache(monkeypatch):
    cc.reset_scene_cache()
    monkeypatch.setenv("COPERNICUS_CLIENT_ID", "id-value")
    monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "secret-value")
    responses = [
        FakeResponse(200, payload={"access_token": "token-1", "expires_in": 3600}),
        FakeResponse(200, content=_tar_bytes()),
    ]
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return responses.pop(0)

    monkeypatch.setattr(cc.requests, "post", fake_post)
    client = cc.CopernicusClient()
    bbox = [10.0, 20.0, 10.01, 20.01]
    first = client.fetch_scene(bbox, _scene(), output_size=(64, 64))
    second = client.fetch_scene(bbox, _scene(), output_size=(64, 64))
    assert len(calls) == 2  # one token call, one scene download
    assert first.get("cached") is None
    assert second["cached"] is True
    assert second["rgb"] == b"rgb-bytes"
    stats = cc.get_scene_cache().stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_scene_cache_enforces_entry_and_byte_bounds():
    cache = cc.reset_scene_cache(max_bytes=4096, max_entries=2)
    for index in range(3):
        cache.put((index,), {"rgb": b"x" * 100, "indices": b"", "indices_ext": b""})
    stats = cache.stats()
    assert stats["entries"] == 2
    assert stats["evictions"] >= 1
    assert stats["bytes"] <= 4096

    small = cc.reset_scene_cache(max_bytes=1024, max_entries=10)
    small.put(("big",), {"rgb": b"x" * 2048, "indices": b"", "indices_ext": b""})
    assert small.stats()["entries"] == 0
    cc.reset_scene_cache()


def test_health_reports_cnn_and_spectral_availability(monkeypatch, tmp_path):
    missing = tmp_path / "missing.onnx"
    monkeypatch.setattr(app_module, "MODEL_ONNX_PATH", missing)
    client = TestClient(app_module.app)
    payload = client.get("/health").json()
    assert payload["status"] == "ok"
    assert payload["cnn_available"] is False
    assert payload["spectral_available"] is True
    assert payload["model_present"] is False
