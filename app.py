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
import copernicus_client as copernicus
import learned_pipeline
from copernicus_client import CopernicusError, MissingCredentialsError, NoScenesError
from geocoding import geocode_place, suggest_places
from exports import csv_bytes, geojson_bytes
from live_pipeline import (
    CLOUD_WARN_PERCENT,
    DEFAULT_WINDOW_DAYS,
    MAX_ANALYSIS_PX,
    MAX_AOI_KM,
    FullyMaskedError,
    analyse_pair,
    build_ndvi_timeline,
)
from profiles import all_profiles_public
from provenance import build_provenance, get_commit_hash
from scene_selection import date_window, rank_scenes, season_warning, validate_aoi
from spectral_pipeline import SpectralConfig, decode_indices, detect_from_indices
from tiling import tiled_predict
from reports import build_report
from history_store import save_analysis, list_analyses, get_analysis
import tempfile
import os
import logging
import sys
from datetime import date
from pathlib import Path

logger = logging.getLogger("satellite_change")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

class SceneSearchRequest(BaseModel):
    bbox: List[float]
    date_before: str
    date_after: str
    window_days: int = DEFAULT_WINDOW_DAYS


class LiveRequest(BaseModel):
    bbox: Optional[List[float]] = None
    place_name: Optional[str] = None
    date_before: str
    date_after: str
    window_days: int = DEFAULT_WINDOW_DAYS
    scene_before_id: Optional[str] = None
    scene_after_id: Optional[str] = None
    profile: str = "general"
    mmu_ha: Optional[float] = None
    composite_scenes: int = 1
    normalise: bool = False
    cleanup: bool = False
    include_road_context: bool = False


class TimelineRequest(BaseModel):
    bbox: List[float]
    dates: List[str]
    window_days: int = 10


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


@app.get("/learned-model-status")
async def learned_model_status_endpoint():
    """Report the optional joblib model without making it a startup dependency."""
    return learned_pipeline.model_status(attempt_load=True)


@app.post("/predict-learned")
async def predict_learned(
    bands_before: UploadFile = File(...),
    bands_after: UploadFile = File(...),
):
    """Optional experimental pipeline; accepts .npz reflectance bands, not RGB PNGs."""
    if not learned_pipeline.is_enabled():
        return JSONResponse(
            status_code=503,
            content={
                "error": "The learned pixel pipeline is disabled.",
                "code": "learned_pipeline_disabled",
                "hint": "Set ENABLE_LEARNED_MODEL=1 and LEARNED_MODEL_PATH to an OSCD-trained joblib artifact.",
                "model": learned_pipeline.model_status(),
            },
        )
    before_bytes = await bands_before.read()
    after_bytes = await bands_after.read()
    try:
        bands_a = learned_pipeline.bands_from_npz(before_bytes)
        bands_b = learned_pipeline.bands_from_npz(after_bytes)
        mask, probability, meta = learned_pipeline.predict_change(bands_a, bands_b)
    except learned_pipeline.LearnedModelUnavailable as exc:
        return JSONResponse(
            status_code=503,
            content={
                "error": str(exc),
                "code": "learned_model_unavailable",
                "hint": "Train the optional joblib model on OSCD TRAIN cities or use the spectral/live path.",
                "model": learned_pipeline.model_status(),
            },
        )
    except (ValueError, KeyError) as exc:
        return JSONResponse(status_code=400, content={"error": str(exc), "code": "invalid_bands"})

    rgb_a = learned_pipeline.rgb_from_bands(bands_a)
    rgb_b = learned_pipeline.rgb_from_bands(bands_b)
    regions = reason_regions(rgb_a, rgb_b, mask)
    overlay = rgb_b.copy()
    overlay[mask == 1] = [255, 0, 0]
    blended = Image.blend(Image.fromarray(rgb_b), Image.fromarray(overlay), alpha=0.5)
    result = {
        "percent_changed": float(mask.mean() * 100.0),
        "image_a_base64": _encode_image(Image.fromarray(rgb_a)),
        "image_b_base64": _encode_image(Image.fromarray(rgb_b)),
        "mask_base64": _encode_image(Image.fromarray(mask * 255)),
        "overlay_base64": _encode_image(blended),
        "probabilities_base64": _encode_image(Image.fromarray((probability * 255).astype(np.uint8))),
        "change_regions": regions,
        "pipeline": "learned_pixel",
        "profile": "learned_oscd_urban",
        "profile_label": "Learned OSCD urban-change classifier (experimental)",
        "percent_cloud_masked": None,
        "validation_status": "experimental; trained on OSCD training cities only; test-set score not available here",
        "display_metrics": False,
        "model": meta,
        "image_shape": [int(mask.shape[0]), int(mask.shape[1])],
    }
    result["provenance"] = build_provenance(
        "learned_pixel",
        profile="learned_oscd_urban",
        thresholds={"probability": meta["threshold"]},
        extra={
            "model": {"path": meta["model"], "feature_count": meta["feature_count"]},
            "options": {"input": "Sentinel-2 L2A reflectance .npz", "bands": list(learned_pipeline.BAND_KEYS)},
        },
    )
    result["history_id"] = save_analysis(
        result,
        {
            "route": "/predict-learned",
            "bands_before": bands_before.filename,
            "bands_after": bands_after.filename,
            "threshold": meta["threshold"],
        },
    )
    return JSONResponse(content=result)

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

def _error(status: int, code: str, message: str, hint: str | None = None, details: dict | None = None) -> JSONResponse:
    payload = {"error": message, "code": code}
    if hint:
        payload["hint"] = hint
    if details:
        payload["details"] = details
    return JSONResponse(status_code=status, content=payload)


def _live_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, MissingCredentialsError):
        return _error(
            400,
            "missing_credentials",
            str(exc),
            "Add COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET to the server environment, or use upload mode.",
        )
    if isinstance(exc, NoScenesError):
        return _error(404, "no_scenes", str(exc), "Widen the ± window, move the dates, or check the AOI.")
    if isinstance(exc, FullyMaskedError):
        return _error(422, "fully_masked", str(exc), details=exc.details)
    if isinstance(exc, ValueError):
        return _error(400, "invalid_request", str(exc))
    if isinstance(exc, CopernicusError):
        return _error(502, "upstream_error", str(exc), "Copernicus may be unavailable; retry later.")
    logger.exception("Unhandled live-analysis error")
    return _error(500, "internal_error", "The analysis failed unexpectedly. The server log has the traceback.")


def _catalog_windows(bbox: list[float], date_before: str, date_after: str, window_days: int) -> dict:
    try:
        before_date = date.fromisoformat(str(date_before)[:10])
        after_date = date.fromisoformat(str(date_after)[:10])
    except ValueError as exc:
        raise ValueError("Dates must be valid ISO dates (YYYY-MM-DD).") from exc
    if before_date >= after_date:
        raise ValueError("The before date must be earlier than the after date.")
    window_days = max(1, min(int(window_days), 120))
    aoi = validate_aoi(bbox, max_km=MAX_AOI_KM, max_px=MAX_ANALYSIS_PX)
    if not aoi["valid"]:
        raise ValueError(aoi["message"])
    client = copernicus.get_client()
    out = {"aoi": aoi, "window_days": window_days, "season_warning": season_warning(date_before, date_after)}
    warnings = []
    for key, target in (("before", date_before), ("after", date_after)):
        features = client.search_scenes(bbox, target, window_days=window_days)
        ranked = rank_scenes(features, bbox, target, window_days=window_days, top=5)
        start, end = date_window(target, window_days)
        recommended = next((row["id"] for row in ranked if row.get("recommended")), None)
        out[key] = {
            "requested_date": str(target)[:10],
            "start": start,
            "end": end,
            "scenes": ranked,
            "recommended_id": recommended,
        }
        if not ranked:
            raise NoScenesError(f"No usable scenes near {target}.")
        if ranked[0]["coverage_percent"] < 99.5:
            warnings.append(
                {
                    "code": "coverage",
                    "severity": "info",
                    "window": key,
                    "message": (
                        f"Top {key} scene footprint covers about {ranked[0]['coverage_percent']:.1f}% "
                        "of the AOI (bounding-box approximation)."
                    ),
                }
            )
    if out["season_warning"]:
        warnings.append({"code": "season", "severity": "warning", "message": out["season_warning"]})
    out["warnings"] = warnings
    out["credentials_present"] = bool(
        os.environ.get("COPERNICUS_CLIENT_ID") and os.environ.get("COPERNICUS_CLIENT_SECRET")
    )
    return out


@app.get("/config")
async def config():
    return {
        "max_aoi_km": MAX_AOI_KM,
        "default_window_days": DEFAULT_WINDOW_DAYS,
        "cloud_warn_percent": CLOUD_WARN_PERCENT,
        "max_analysis_px": MAX_ANALYSIS_PX,
        "profiles": all_profiles_public(),
        "model_present": MODEL_ONNX_PATH.is_file(),
        "commit": get_commit_hash(),
        "version": "3.0.0",
    }


@app.get("/profiles")
async def profiles():
    return {"profiles": all_profiles_public()}


@app.post("/scenes")
async def scenes(req: SceneSearchRequest):
    """Catalog search + ranking only. No imagery is downloaded."""
    try:
        return JSONResponse(content=_catalog_windows(req.bbox, req.date_before, req.date_after, req.window_days))
    except Exception as exc:
        return _live_error(exc)


@app.post("/fetch-and-predict")
async def fetch_and_predict(req: LiveRequest):
    bbox = req.bbox
    place = None
    if bbox is None:
        if not req.place_name:
            return _error(400, "invalid_request", "Provide an AOI bbox or a place_name.")
        try:
            place, bbox = geocode_place(req.place_name)
        except ValueError as exc:
            return _error(400, "place_not_found", str(exc))
        except Exception as exc:
            return _error(502, "geocoding_error", f"Failed to geocode place: {exc}")
    if req.mmu_ha is not None and not 0 <= req.mmu_ha <= 100:
        return _error(400, "invalid_request", "mmu_ha must be between 0 and 100 hectares.")
    if not 1 <= int(req.composite_scenes) <= 3:
        return _error(400, "invalid_request", "composite_scenes must be between 1 and 3.")
    try:
        result = analyse_pair(
            copernicus.get_client(),
            list(bbox),
            req.date_before,
            req.date_after,
            window_days=req.window_days,
            scene_before_id=req.scene_before_id,
            scene_after_id=req.scene_after_id,
            profile_key=req.profile,
            mmu_ha=req.mmu_ha,
            composite_scenes=req.composite_scenes,
            normalise=req.normalise,
            cleanup=req.cleanup,
            include_road_context=req.include_road_context,
            place_name=place,
        )
    except Exception as exc:
        return _live_error(exc)
    if place:
        result["resolved_place_name"] = place
    result["history_id"] = save_analysis(
        result,
        {
            "route": "/fetch-and-predict",
            "bbox": bbox,
            "place_name": place,
            "date_before": req.date_before,
            "date_after": req.date_after,
            "window_days": req.window_days,
            "scene_before_id": req.scene_before_id,
            "scene_after_id": req.scene_after_id,
            "profile": req.profile,
            "mmu_ha": req.mmu_ha,
            "composite_scenes": req.composite_scenes,
            "normalise": req.normalise,
            "cleanup": req.cleanup,
        },
        place,
    )
    return JSONResponse(content=result)


@app.post("/timeline")
async def timeline(req: TimelineRequest):
    try:
        return JSONResponse(
            content=build_ndvi_timeline(
                copernicus.get_client(),
                req.bbox,
                req.dates,
                window_days=req.window_days,
                max_aoi_km=MAX_AOI_KM,
            )
        )
    except Exception as exc:
        return _live_error(exc)


def _export_response(result: dict, fmt: str) -> Response:
    fmt = fmt.lower()
    if fmt == "geojson":
        return Response(
            content=geojson_bytes(result),
            media_type="application/geo+json",
            headers={"Content-Disposition": 'attachment; filename="change-regions.geojson"'},
        )
    if fmt == "csv":
        return Response(
            content=csv_bytes(result),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="change-regions.csv"'},
        )
    raise HTTPException(status_code=404, detail="Unknown export format; use geojson or csv.")


@app.post("/export/{fmt}")
async def export_result(fmt: str, req: ReportRequest):
    if not isinstance(req.result, dict):
        raise HTTPException(status_code=400, detail="result must be an object")
    return _export_response(req.result, fmt)


@app.get("/history/{analysis_id}/export/{fmt}")
async def export_history(analysis_id: int, fmt: str):
    item = get_analysis(analysis_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _export_response(item["result"], fmt)


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
