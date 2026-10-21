from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

# Load environment variables from .env
load_dotenv()
import hashlib
import numpy as np
from PIL import Image
import io
import base64

from change_reasoner import reason_regions
from copernicus_client import fetch_satellite_image
from geocoding import geocode_place, suggest_places
from provenance import build_provenance, get_commit_hash
from spectral_pipeline import SpectralConfig, decode_indices, detect_from_indices
from tiling import tiled_predict
from reports import build_report
from history_store import save_analysis, list_analyses, get_analysis
import tempfile
import os
import logging
import sys
from pathlib import Path

logger = logging.getLogger("satellite_change")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

class FetchRequest(BaseModel):
    bbox: Optional[List[float]] = None
    place_name: Optional[str] = None
    date_before: str
    date_after: str

class ReportRequest(BaseModel):
    result: dict

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

MODEL_ONNX_PATH = Path(os.environ.get("MODEL_ONNX_PATH", "model.onnx"))
EXPECTED_ONNX_BYTES = 33268410
session = None
_model_error: str | None = None
_model_fingerprint: tuple[int, int] | None = None


class ModelUnavailable(RuntimeError):
    """Raised when the optional CNN cannot be loaded; the spectral path stays usable."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_status(attempt_load: bool = False) -> dict:
    """Report model presence and loadability without ever modifying the file."""
    global _model_error, _model_fingerprint
    path = MODEL_ONNX_PATH
    if not path.is_file():
        return {
            "present": False,
            "path": str(path),
            "expected_bytes": EXPECTED_ONNX_BYTES,
            "error": f"No ONNX model at {path}. Set MODEL_ONNX_PATH or copy the Drive model.onnx (expected {EXPECTED_ONNX_BYTES} bytes).",
        }
    stat = path.stat()
    fingerprint = (stat.st_size, stat.st_mtime_ns)
    if attempt_load and (session is None or _model_fingerprint != fingerprint):
        try:
            get_onnx_session()
        except ModelUnavailable as exc:
            _model_error = str(exc)
    return {
        "present": True,
        "path": str(path),
        "size_bytes": stat.st_size,
        "sha256": _file_sha256(path),
        "expected_bytes": EXPECTED_ONNX_BYTES,
        "size_matches_expected": stat.st_size == EXPECTED_ONNX_BYTES,
        "loaded": session is not None,
        "error": _model_error,
    }


def get_onnx_session():
    """Load the optional CNN weights only when Pipeline A is requested."""
    global session, _model_error, _model_fingerprint
    if session is not None:
        return session
    if not MODEL_ONNX_PATH.is_file():
        raise ModelUnavailable(
            f"Pipeline A requires an ONNX model, but {MODEL_ONNX_PATH} is missing. "
            "Set MODEL_ONNX_PATH or copy the Drive model.onnx (expected "
            f"{EXPECTED_ONNX_BYTES} bytes). The spectral/live pipeline is unaffected."
        )
    try:
        import onnxruntime
        stat = MODEL_ONNX_PATH.stat()
        session = onnxruntime.InferenceSession(str(MODEL_ONNX_PATH))
        _model_fingerprint = (stat.st_size, stat.st_mtime_ns)
        _model_error = None
    except Exception as exc:  # InvalidProtobuf, missing runtime, incompatible opset
        size = MODEL_ONNX_PATH.stat().st_size
        digest = _file_sha256(MODEL_ONNX_PATH)
        _model_error = (
            f"model.onnx failed to load ({type(exc).__name__}: {exc}). "
            f"size={size} bytes sha256={digest}. Replace it with the Drive copy "
            f"({EXPECTED_ONNX_BYTES} bytes)."
        )
        session = None
        raise ModelUnavailable(_model_error) from exc
    return session


def reset_model_session() -> None:
    global session, _model_error, _model_fingerprint
    session = None
    _model_error = None
    _model_fingerprint = None


@app.get("/health")
async def health():
    """Container-friendly liveness check that never exposes secrets or loads weights."""
    return {
        "status": "ok",
        "model_present": MODEL_ONNX_PATH.is_file(),
        "model_loaded": session is not None,
        "commit": get_commit_hash(),
    }


@app.get("/model-status")
async def model_status_endpoint():
    return model_status(attempt_load=True)

def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img = img.resize((256, 256))
    img_array = np.array(img).astype(np.float32) / 255.0
    img_array = np.transpose(img_array, (2, 0, 1)) # HWC to CHW
    
    # Normalize with ImageNet stats
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
    img_array = (img_array - mean) / std
    
    # Add batch dimension
    img_array = np.expand_dims(img_array, axis=0).astype(np.float32)
    return img_array

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r") as f:
        return f.read()

def _encode_image(img):
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def _cnn_tile(a_rgb, b_rgb):
    def normalized(rgb):
        array = np.transpose(rgb.astype(np.float32) / 255.0, (2, 0, 1))
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)[:, None, None]
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)[:, None, None]
        return ((array - mean) / std)[None].astype(np.float32)
    logits = get_onnx_session().run(None, {"input_a": normalized(a_rgb), "input_b": normalized(b_rgb)})[0]
    return (1 / (1 + np.exp(np.clip(-logits[0, 0], -88.7, 88.7)))).astype(np.float32)

def run_inference_arrays(img_a_rgb, img_b_rgb):
    """Pipeline A shared entry point; tiles images above the ONNX native size."""
    probs = tiled_predict(img_a_rgb, img_b_rgb, _cnn_tile)
    binary_mask = (probs > 0.5).astype(np.uint8)
    regions = reason_regions(img_a_rgb, img_b_rgb, binary_mask)
    overlay = img_b_rgb.copy(); overlay[binary_mask == 1] = [255, 0, 0]
    return {"percent_changed": float(binary_mask.mean() * 100), "overlay_base64": _encode_image(Image.blend(Image.fromarray(img_b_rgb), Image.fromarray(overlay), .5)), "image_a_base64": _encode_image(Image.fromarray(img_a_rgb)), "image_b_base64": _encode_image(Image.fromarray(img_b_rgb)), "mask_base64": _encode_image(Image.fromarray(binary_mask * 255)), "change_regions": regions, "confidence_base64": _encode_image(Image.fromarray((probs * 255).astype(np.uint8))), "pipeline": "cnn", "profile": "general", "provenance": build_provenance("cnn", profile="general")}

def run_inference_pipeline(img_a_bytes, img_b_bytes):
    try:
        # Decode without resizing: tiled_predict preserves full-size uploads.
        Image.open(io.BytesIO(img_a_bytes)).verify()
        Image.open(io.BytesIO(img_b_bytes)).verify()
    except Exception as e:
        return {"error": f"Invalid image file(s) provided. {str(e)}"}
    
    # 256px files take one native ONNX tile; larger files retain their dimensions.
    img_a_rgb = np.array(
        Image.open(io.BytesIO(img_a_bytes)).convert('RGB'),
        dtype=np.uint8
    )
    img_b_rgb = np.array(
        Image.open(io.BytesIO(img_b_bytes)).convert('RGB'),
        dtype=np.uint8
    )
    return run_inference_arrays(img_a_rgb, img_b_rgb)

def spectral_change_detection(rgb_a_bytes, rgb_b_bytes, idx_a_bytes, idx_b_bytes, config=SpectralConfig()):
    # 1. Decode images
    img_a_rgb = np.array(Image.open(io.BytesIO(rgb_a_bytes)).convert('RGB').resize((256, 256)), dtype=np.uint8)
    img_b_rgb = np.array(Image.open(io.BytesIO(rgb_b_bytes)).convert('RGB').resize((256, 256)), dtype=np.uint8)
    idx_a = np.array(Image.open(io.BytesIO(idx_a_bytes)).convert('RGB').resize((256, 256)), dtype=np.float32)
    idx_b = np.array(Image.open(io.BytesIO(idx_b_bytes)).convert('RGB').resize((256, 256)), dtype=np.float32)
    
    ndvi_a, ndbi_a, scl_a = decode_indices(idx_a)
    ndvi_b, ndbi_b, scl_b = decode_indices(idx_b)
    binary_mask, cloud_mask, threshold_info = detect_from_indices(ndvi_a, ndbi_a, ndvi_b, ndbi_b, scl_a, scl_b, config)
    
    # 4. Generate Visualization
    change_regions = reason_regions(img_a_rgb, img_b_rgb, binary_mask, idx_a=idx_a, idx_b=idx_b)
    
    percent_changed = float(binary_mask.mean() * 100)
    
    # Create an overlay (red for changes)
    original_img_a = Image.open(io.BytesIO(rgb_a_bytes)).convert('RGB').resize((256, 256))
    original_img_b = Image.open(io.BytesIO(rgb_b_bytes)).convert('RGB').resize((256, 256))
    overlay = np.array(original_img_b)
    overlay[binary_mask == 1] = [255, 0, 0] # Red
    
    # Blend overlay with original using PIL
    blended = Image.blend(original_img_b, Image.fromarray(overlay), alpha=0.5)
    
    # Encode all images to base64
    mask_img = Image.fromarray(binary_mask * 255)
    # Continuous evidence is used by the UI heatmap, not thresholded change stats.
    evidence = np.maximum(np.maximum(ndvi_a - ndvi_b, 0), np.maximum(ndbi_b - ndbi_a, 0))
    scale = float(np.nanpercentile(evidence, 99)) if np.isfinite(evidence).any() else 0.0
    confidence = np.clip(evidence / scale, 0, 1) if scale > 1e-8 else np.zeros_like(evidence)
    
    return {
        "percent_changed": float(percent_changed),
        "overlay_base64": _encode_image(blended), "image_a_base64": _encode_image(original_img_a),
        "image_b_base64": _encode_image(original_img_b), "mask_base64": _encode_image(mask_img),
        "change_regions": change_regions, "percent_cloud_masked": threshold_info["masked_percent"],
        "thresholds": threshold_info, "pipeline": "spectral", "confidence_base64": _encode_image(Image.fromarray((confidence * 255).astype(np.uint8)))
    }

@app.post("/predict")
async def predict(image_a: UploadFile = File(...), image_b: UploadFile = File(...)):
    img_a_bytes = await image_a.read()
    img_b_bytes = await image_b.read()

    try:
        result = run_inference_pipeline(img_a_bytes, img_b_bytes)
    except ModelUnavailable as exc:
        status = model_status()
        return JSONResponse(
            status_code=503,
            content={
                "error": str(exc),
                "code": "model_unavailable",
                "hint": "The live Sentinel-2 spectral path still works without model.onnx.",
                "model": status,
            },
        )
    if "error" in result:
        return JSONResponse(status_code=400, content={"error": result["error"], "code": "invalid_image"})

    result["history_id"] = save_analysis(result, {"route": "/predict", "image_a": image_a.filename, "image_b": image_b.filename})
    return JSONResponse(content=result)

@app.post("/report")
async def download_report(req: ReportRequest):
    """Render a self-contained PDF from a completed API response."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            build_report(req.result, tmp.name)
            return Response(content=open(tmp.name, "rb").read(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=change-report.pdf"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not generate report: {exc}")

@app.get("/history")
async def history(limit: int = 50):
    return list_analyses(limit)

@app.get("/history/{analysis_id}")
async def history_detail(analysis_id: int):
    item = get_analysis(analysis_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return item

@app.post("/fetch-and-predict")
async def fetch_and_predict(req: FetchRequest):
    bbox = req.bbox
    resolved_place = None

    if req.place_name:
        try:
            resolved_place, bbox = geocode_place(req.place_name)
        except ValueError as e:
            return JSONResponse(status_code=400, content={"error": str(e)})
        except Exception as e:
            return JSONResponse(status_code=502, content={"error": f"Failed to geocode place: {str(e)}"})
    elif not bbox or len(bbox) != 4:
        return JSONResponse(status_code=400, content={"error": "Either a valid place_name or a 4-float bbox must be provided."})
        
    try:
        rgb_a_bytes, idx_a_bytes, cloud_before = fetch_satellite_image(bbox, req.date_before)
        rgb_b_bytes, idx_b_bytes, cloud_after = fetch_satellite_image(bbox, req.date_after)
    except ValueError as e:
        # E.g. Missing credentials
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        # E.g. Network error or Sentinel Hub error
        return JSONResponse(status_code=502, content={"error": f"Failed to fetch imagery: {str(e)}"})
        
    result = spectral_change_detection(rgb_a_bytes, rgb_b_bytes, idx_a_bytes, idx_b_bytes)
    if "error" in result:
        return JSONResponse(status_code=400, content={"error": result["error"]})
        
    result["cloud_coverage_before"] = cloud_before
    result["cloud_coverage_after"] = cloud_after
    result["resolved_bbox"] = bbox
    if resolved_place:
        result["resolved_place_name"] = resolved_place
        
    # Story Mode Summary Sentence
    pct = result["percent_changed"]
    if pct < 5: severity = "minimal"
    elif pct < 15: severity = "moderate"
    else: severity = "significant"
    
    valid_regions = [r for r in result["change_regions"] if r["change_type"] != "Possible cloud interference"]
    if valid_regions:
        area_by_type = {}
        for r in valid_regions:
            area_by_type[r["change_type"]] = area_by_type.get(r["change_type"], 0) + r["pixel_area"]
        dominant_category = max(area_by_type.items(), key=lambda x: x[1])[0].lower()
    else:
        dominant_category = "unclear changes"
        
    place_str = resolved_place or "the selected location"
    summary_sentence = f"Satellite analysis of {place_str} between {req.date_before} and {req.date_after} shows {severity} change, with approximately {pct:.2f}% of the observed area affected — primarily {dominant_category}."
    result["summary_sentence"] = summary_sentence
    result["date_before"] = req.date_before
    result["date_after"] = req.date_after
    result["history_id"] = save_analysis(result, {"route": "/fetch-and-predict", "bbox": bbox, "date_before": req.date_before, "date_after": req.date_after}, resolved_place)
    
    return JSONResponse(content=result)

@app.get("/geocode-suggest")
async def geocode_suggest(q: str):
    if not q or len(q.strip()) < 2:
        return JSONResponse(status_code=400, content={"error": "Query too short"})
    try:
        results = suggest_places(q.strip())
        return JSONResponse(content=results)
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
