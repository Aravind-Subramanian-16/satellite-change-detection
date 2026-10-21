import io
import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

import app as app_module


def _png(colour=(10, 20, 30)):
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), colour).save(buffer, "PNG")
    return buffer.getvalue()


def _set_model(monkeypatch, path: Path):
    monkeypatch.setattr(app_module, "MODEL_ONNX_PATH", path)
    app_module.reset_model_session()


def test_missing_model_is_reported_and_predict_returns_503(monkeypatch, tmp_path):
    _set_model(monkeypatch, tmp_path / "missing.onnx")
    client = TestClient(app_module.app)
    status = client.get("/model-status").json()
    assert status["present"] is False
    assert "No ONNX model" in status["error"]
    response = client.post(
        "/predict",
        files={"image_a": ("a.png", _png(), "image/png"), "image_b": ("b.png", _png(), "image/png")},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "model_unavailable"
    assert client.get("/health").status_code == 200


def test_corrupt_model_reports_size_and_sha_without_crashing(monkeypatch, tmp_path):
    payload = b"this is not a protobuf"
    path = tmp_path / "model.onnx"
    path.write_bytes(payload)
    _set_model(monkeypatch, path)
    client = TestClient(app_module.app)
    status = client.get("/model-status").json()
    assert status["present"] is True
    assert status["size_bytes"] == len(payload)
    assert status["sha256"] == hashlib.sha256(payload).hexdigest()
    assert status["loaded"] is False
    assert "failed to load" in status["error"]
    response = client.post(
        "/predict",
        files={"image_a": ("a.png", _png(), "image/png"), "image_b": ("b.png", _png(), "image/png")},
    )
    assert response.status_code == 503
    assert client.get("/health").json()["model_loaded"] is False
