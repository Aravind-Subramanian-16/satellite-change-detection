"""Model-loading failures are clear API errors rather than unhandled crashes."""
import io

import onnxruntime
from fastapi.testclient import TestClient
from PIL import Image
import pytest

import app as app_module


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_invalid_onnx_model_has_actionable_runtime_error(tmp_path, monkeypatch):
    model_path = tmp_path / "invalid.onnx"
    model_path.touch()
    monkeypatch.setattr(app_module, "MODEL_ONNX_PATH", model_path)
    app_module.reset_model_session()
    monkeypatch.setattr(
        onnxruntime,
        "InferenceSession",
        lambda _path: (_ for _ in ()).throw(RuntimeError("InvalidProtobuf")),
    )

    with pytest.raises(app_module.ModelUnavailable, match="InvalidProtobuf.*Drive copy.*33268410"):
        app_module.get_onnx_session()
    app_module.reset_model_session()


def test_predict_returns_service_unavailable_for_invalid_onnx(tmp_path, monkeypatch):
    model_path = tmp_path / "invalid.onnx"
    model_path.touch()
    monkeypatch.setattr(app_module, "MODEL_ONNX_PATH", model_path)
    app_module.reset_model_session()
    monkeypatch.setattr(
        onnxruntime,
        "InferenceSession",
        lambda _path: (_ for _ in ()).throw(RuntimeError("InvalidProtobuf")),
    )
    client = TestClient(app_module.app)

    response = client.post(
        "/predict",
        files={"image_a": ("a.png", _png(), "image/png"), "image_b": ("b.png", _png(), "image/png")},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "model_unavailable"
    assert "33268410" in payload["error"]
    assert "InvalidProtobuf" in payload["error"]
    app_module.reset_model_session()
