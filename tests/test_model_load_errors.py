"""Model-loading failures are clear API errors rather than unhandled crashes."""
import io

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
    monkeypatch.setattr(app_module, "session", None)
    monkeypatch.setattr(
        app_module.onnxruntime,
        "InferenceSession",
        lambda _path: (_ for _ in ()).throw(RuntimeError("InvalidProtobuf")),
    )

    with pytest.raises(RuntimeError, match="verified Drive model.onnx.*33,268,410 bytes.*InvalidProtobuf"):
        app_module.get_onnx_session()


def test_predict_returns_service_unavailable_for_invalid_onnx(tmp_path, monkeypatch):
    model_path = tmp_path / "invalid.onnx"
    model_path.touch()
    monkeypatch.setattr(app_module, "MODEL_ONNX_PATH", model_path)
    monkeypatch.setattr(app_module, "session", None)
    monkeypatch.setattr(
        app_module.onnxruntime,
        "InferenceSession",
        lambda _path: (_ for _ in ()).throw(RuntimeError("InvalidProtobuf")),
    )
    client = TestClient(app_module.app)

    response = client.post(
        "/predict",
        files={"image_a": ("a.png", _png(), "image/png"), "image_b": ("b.png", _png(), "image/png")},
    )

    assert response.status_code == 503
    assert "replace it with the verified Drive model.onnx" in response.json()["detail"]
    assert "InvalidProtobuf" in response.json()["detail"]
