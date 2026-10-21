import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as app_module
import learned_pipeline
import security

client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def clean_rate_limiter():
    security.reset_rate_limiter(app_module.app)
    yield
    security.reset_rate_limiter(app_module.app)


def _png(width=8, height=8):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (40, 90, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def _npz(shape=(4, 4)):
    bands = {
        key: np.full(shape, 1000.0, dtype=np.float32)
        for key in ("B02", "B03", "B04", "B08", "B11", "B12")
    }
    buffer = io.BytesIO()
    np.savez(buffer, **bands)
    return buffer.getvalue()


def test_security_headers_and_request_id_are_always_present():
    response = client.get("/health", headers={"X-Request-ID": "test-request-1"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-1"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_unsafe_request_id_is_replaced():
    response = client.get("/health", headers={"X-Request-ID": "bad id <script>"})
    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert request_id != "bad id <script>"
    assert len(request_id) == 32


def test_error_payload_carries_request_id_and_no_store():
    response = client.post(
        "/timeline",
        json={"bbox": [0, 0, 0, 0], "dates": ["2024-01-01"], "window_days": 10},
        headers={"X-Request-ID": "err-123"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["request_id"] == "err-123"
    assert response.headers["cache-control"] == "no-store"


def test_cross_origin_requests_are_not_enabled_by_default():
    response = client.options(
        "/predict",
        headers={
            "Origin": "https://example.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_rate_limit_rejects_second_request(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    security.reset_rate_limiter(app_module.app)
    first = client.post("/timeline", json={"bbox": [0, 0, 0, 0], "dates": []})
    second = client.post("/timeline", json={"bbox": [0, 0, 0, 0], "dates": []})
    assert first.status_code == 400
    assert second.status_code == 429
    assert second.json()["code"] == "rate_limited"
    assert int(second.headers["retry-after"]) >= 1


def test_image_upload_rejects_wrong_type_and_oversized_file(monkeypatch):
    wrong = client.post(
        "/predict",
        files={
            "image_a": ("before.gif", b"GIF89a", "image/gif"),
            "image_b": ("after.png", _png(), "image/png"),
        },
    )
    assert wrong.status_code == 415
    assert wrong.json()["code"] == "unsupported_file_type"

    monkeypatch.setenv("MAX_UPLOAD_MB", "0.0001")
    oversized = client.post(
        "/predict",
        files={
            "image_a": ("before.png", _png() * 4, "image/png"),
            "image_b": ("after.png", _png(), "image/png"),
        },
    )
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "file_too_large"


def test_image_upload_rejects_invalid_pixels_and_excessive_dimensions(monkeypatch):
    invalid = client.post(
        "/predict",
        files={
            "image_a": ("before.png", b"not an image", "image/png"),
            "image_b": ("after.png", _png(), "image/png"),
        },
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "invalid_image"

    monkeypatch.setenv("MAX_IMAGE_PIXELS", "10")
    too_large = client.post(
        "/predict",
        files={
            "image_a": ("before.png", _png(8, 8), "image/png"),
            "image_b": ("after.png", _png(8, 8), "image/png"),
        },
    )
    assert too_large.status_code == 413
    assert too_large.json()["code"] == "image_too_large"


def test_learned_upload_rejects_bad_extension_and_pixel_bomb(monkeypatch):
    wrong = client.post(
        "/predict-learned",
        files={
            "bands_before": ("before.zip", b"PK", "application/zip"),
            "bands_after": ("after.npz", _npz(), "application/octet-stream"),
        },
        headers={"X-Request-ID": "learned-1"},
    )
    assert wrong.status_code == 503 or wrong.status_code == 415

    monkeypatch.setenv("ENABLE_LEARNED_MODEL", "1")
    monkeypatch.setenv("MAX_LEARNED_PIXELS", "4")
    huge = client.post(
        "/predict-learned",
        files={
            "bands_before": ("before.npz", _npz((4, 4)), "application/octet-stream"),
            "bands_after": ("after.npz", _npz((4, 4)), "application/octet-stream"),
        },
    )
    assert huge.status_code == 400
    assert "limit" in huge.json()["error"]


def test_npz_reader_limits_declared_uncompressed_size(monkeypatch):
    monkeypatch.setenv("MAX_NPZ_UNCOMPRESSED_MB", "0.00001")
    with pytest.raises(ValueError, match="memory limit"):
        learned_pipeline.bands_from_npz(_npz())


def test_npz_reader_rejects_non_2d_bands():
    payload = io.BytesIO()
    np.savez(
        payload,
        B02=np.zeros((2, 2, 2), dtype=np.float32),
        B03=np.zeros((2, 2), dtype=np.float32),
        B04=np.zeros((2, 2), dtype=np.float32),
        B08=np.zeros((2, 2), dtype=np.float32),
        B11=np.zeros((2, 2), dtype=np.float32),
        B12=np.zeros((2, 2), dtype=np.float32),
    )
    with pytest.raises(ValueError, match="2-D"):
        learned_pipeline.bands_from_npz(payload.getvalue())


def test_request_body_limit_is_enforced_before_parsing(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_MB", "0.00001")
    response = client.post(
        "/report",
        json={"result": {"padding": "x" * 4096}},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"


def test_secret_redaction_covers_env_values_and_key_value_patterns(monkeypatch):
    monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "super-secret-value")
    text = "OAuth client_secret=super-secret-value Authorization: Bearer abc123"
    redacted = security.redact_secrets(text)
    assert "super-secret-value" not in redacted
    assert "abc123" not in redacted
    assert "[redacted]" in redacted
