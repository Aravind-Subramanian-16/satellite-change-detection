import numpy as np
from spectral_pipeline import SpectralConfig, detect_from_indices
from tiling import tiled_predict

def test_stitching_known_mask_reproduces_values():
    a=np.zeros((513, 501, 3), np.uint8); known=np.arange(a.shape[0]*a.shape[1], dtype=np.float32).reshape(a.shape[:2])
    output=tiled_predict(a,a,lambda x,y: known[:x.shape[0],:x.shape[1]], tile=256, overlap=32)
    # Constant predictor is a stricter seam test than coordinate-local values.
    constant=tiled_predict(a,a,lambda x,y: np.ones(x.shape[:2],np.float32)*.37, tile=256, overlap=32)
    assert output.shape == known.shape and np.allclose(constant,.37)

def test_cloud_classes_are_excluded():
    z=np.zeros((2,2),np.float32); scl=np.array([[8,0],[0,10]],np.uint8)
    mask, invalid, meta=detect_from_indices(z,z,z-.5,z+.5,scl,scl)
    assert invalid.sum()==2 and mask.sum()==2 and meta["masked_percent"]==50.0

def test_adaptive_degenerate_inputs_have_safe_fallbacks():
    z=np.zeros((8,8),np.float32)
    mask, _, meta=detect_from_indices(z,z,z,z,config=SpectralConfig(mode="otsu"))
    assert mask.sum()==0 and meta["ndvi_drop_threshold"] == -.15 and meta["ndbi_rise_threshold"] == .1
