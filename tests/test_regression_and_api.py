import json
import os
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app import app, run_inference_pipeline
from spectral_pipeline import SpectralConfig, detect_from_indices

FIXTURE=json.loads((Path(__file__).parent/'fixtures/regression.json').read_text())
MODEL_ONNX_PATH = Path(os.environ.get("MODEL_ONNX_PATH", "model.onnx"))

@pytest.mark.skipif(not MODEL_ONNX_PATH.is_file(), reason="Pipeline A regression test requires model.onnx (set MODEL_ONNX_PATH)")
def test_pipeline_a_fixed_sample_is_within_tolerance():
    image=(Path('dataset/test/A/test_100_0_0.png')).read_bytes()
    result=run_inference_pipeline(image,image)
    expected=FIXTURE['cnn_same_image']
    assert abs(result['percent_changed']-expected['percent_changed']) <= .01
    assert len(result['change_regions']) == expected['regions']

def test_pipeline_b_fixed_spectral_fixture_is_within_tolerance():
    before=np.zeros((2,2),np.float32); after=before.copy(); after[0,1]=-.5; after[1,0]=-.5
    scl=np.array([[0,8],[0,0]],np.uint8)
    mask, _, info=detect_from_indices(before,before,after,before,scl,scl,SpectralConfig())
    assert abs(mask.mean()*100-FIXTURE['spectral_synthetic']['percent_changed']) <= .01
    assert abs(info['masked_percent']-FIXTURE['spectral_synthetic']['masked_percent']) <= .01

def test_history_endpoints(tmp_path, monkeypatch):
    import history_store
    monkeypatch.setattr(history_store, 'DB_PATH', tmp_path/'history.sqlite3')
    client=TestClient(app)
    result={"pipeline":"spectral","percent_changed":2.0,"change_regions":[]}
    from history_store import save_analysis
    ident=save_analysis(result,{"route":"test"},"test-place")
    assert client.get('/history').status_code == 200
    detail=client.get(f'/history/{ident}')
    assert detail.status_code == 200 and detail.json()['location'] == 'test-place'
    assert client.get('/history/999999').status_code == 404
