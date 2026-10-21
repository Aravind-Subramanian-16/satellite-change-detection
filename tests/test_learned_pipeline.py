import io

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app as app_module
import learned_pipeline
import history_store
from learned_features import BAND_KEYS, build_pixel_features


def _bands(shape=(6, 6), offset=0.0):
    return {
        key: np.full(shape, 1000.0 + offset + index * 100.0, dtype=np.float32)
        for index, key in enumerate(BAND_KEYS)
    }


def _bundle():
    _, names = build_pixel_features(_bands(), _bands())
    return {
        "model": _ConstantModel(),
        "threshold": 0.5,
        "feature_names": names,
        "metadata": {"fit_cities": ["train_a"], "held_out_train_cities": ["train_b"]},
    }


class _ConstantModel:
    def predict_proba(self, features):
        probability = np.full(features.shape[0], 0.8, dtype=np.float32)
        return np.column_stack([1.0 - probability, probability])


def test_predict_change_returns_mask_probability_and_metadata():
    before = _bands()
    after = _bands(offset=100.0)
    mask, probability, meta = learned_pipeline.predict_change(before, after, bundle=_bundle())

    assert mask.shape == before["B02"].shape
    assert probability.shape == mask.shape
    assert mask.dtype == np.uint8
    assert mask.all()
    assert 0.0 <= float(probability.min()) <= float(probability.max()) <= 1.0
    assert meta["threshold"] == 0.5
    assert meta["predicted_fraction_percent"] == 100.0
    assert "OSCD training cities" in meta["note"]


def test_threshold_override_can_reject_everything():
    mask, _, meta = learned_pipeline.predict_change(
        _bands(), _bands(), bundle=_bundle(), threshold=0.95
    )
    assert not mask.any()
    assert meta["threshold"] == 0.95


def test_feature_layout_mismatch_is_rejected():
    bundle = _bundle()
    bundle["feature_names"] = tuple(reversed(bundle["feature_names"]))
    with pytest.raises(ValueError, match="Feature layout changed"):
        learned_pipeline.predict_change(_bands(), _bands(), bundle=bundle)


def test_missing_model_raises_actionable_error(tmp_path, monkeypatch):
    learned_pipeline.reset_cache()
    monkeypatch.setattr(learned_pipeline, "MODEL_PATH", tmp_path / "missing.joblib")
    with pytest.raises(learned_pipeline.LearnedModelUnavailable, match="LEARNED_MODEL_PATH"):
        learned_pipeline.load_bundle()
    status = learned_pipeline.model_status()
    assert status["present"] is False
    assert "Train" in status["hint"] or "LEARNED_MODEL_PATH" in status["hint"]


def test_npz_reader_requires_all_bands():
    buffer = io.BytesIO()
    np.savez(buffer, **_bands())
    parsed = learned_pipeline.bands_from_npz(buffer.getvalue())
    assert set(parsed) == set(BAND_KEYS)

    missing = _bands()
    missing.pop("B12")
    buffer = io.BytesIO()
    np.savez(buffer, **missing)
    with pytest.raises(ValueError, match="missing bands"):
        learned_pipeline.bands_from_npz(buffer.getvalue())

    with pytest.raises(ValueError, match="Could not read"):
        learned_pipeline.bands_from_npz(b"not-an-npz")


def test_learned_status_and_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(history_store, "DB_PATH", tmp_path / "history.sqlite3")
    monkeypatch.setattr(learned_pipeline, "MODEL_PATH", tmp_path / "missing.joblib")
    monkeypatch.delenv("ENABLE_LEARNED_MODEL", raising=False)
    learned_pipeline.reset_cache()
    client = TestClient(app_module.app)

    status = client.get("/learned-model-status")
    assert status.status_code == 200
    assert status.json()["present"] is False
    assert status.json()["enabled"] is False

    buffer = io.BytesIO()
    np.savez(buffer, **_bands())
    payload = buffer.getvalue()
    disabled = client.post(
        "/predict-learned",
        files={
            "bands_before": ("before.npz", payload, "application/octet-stream"),
            "bands_after": ("after.npz", payload, "application/octet-stream"),
        },
    )
    assert disabled.status_code == 503
    assert disabled.json()["code"] == "learned_pipeline_disabled"

    monkeypatch.setenv("ENABLE_LEARNED_MODEL", "1")
    assert client.get("/learned-model-status").json()["enabled"] is True

    unavailable = client.post(
        "/predict-learned",
        files={
            "bands_before": ("before.npz", payload, "application/octet-stream"),
            "bands_after": ("after.npz", payload, "application/octet-stream"),
        },
    )
    assert unavailable.status_code == 503
    assert unavailable.json()["code"] == "learned_model_unavailable"

    invalid = client.post(
        "/predict-learned",
        files={
            "bands_before": ("before.npz", b"broken", "application/octet-stream"),
            "bands_after": ("after.npz", b"broken", "application/octet-stream"),
        },
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "invalid_bands"

    monkeypatch.setattr(learned_pipeline, "load_bundle", lambda *args, **kwargs: _bundle())
    success = client.post(
        "/predict-learned",
        files={
            "bands_before": ("before.npz", payload, "application/octet-stream"),
            "bands_after": ("after.npz", payload, "application/octet-stream"),
        },
    )
    assert success.status_code == 200, success.text
    data = success.json()
    assert data["pipeline"] == "learned_pixel"
    assert data["display_metrics"] is False
    assert data["percent_changed"] == 100.0
    assert data["history_id"] > 0
    assert data["provenance"]["pipeline"] == "learned_pixel"
    assert data["mask_base64"]
    assert data["probabilities_base64"]
