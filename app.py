from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
import onnxruntime
import numpy as np
from PIL import Image
import io
import base64

from change_reasoner import reason_regions
from copernicus_client import fetch_satellite_image
from geocoding import geocode_place, suggest_places

class FetchRequest(BaseModel):
    bbox: Optional[List[float]] = None
    place_name: Optional[str] = None
    date_before: str
    date_after: str

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

session = onnxruntime.InferenceSession("model.onnx")

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

def run_inference_pipeline(img_a_bytes, img_b_bytes):
    try:
        input_a = preprocess_image(img_a_bytes)
        input_b = preprocess_image(img_b_bytes)
    except Exception as e:
        return {"error": f"Invalid image file(s) provided. {str(e)}"}
    
    ort_inputs = {
        'input_a': input_a,
        'input_b': input_b
    }
    
    # Run inference
    ort_outs = session.run(None, ort_inputs)
    mask = ort_outs[0] # Shape: [1, 1, 256, 256]
    
    # Sigmoid and threshold
    mask = 1 / (1 + np.exp(np.clip(-mask, -88.7, 88.7))) # Sigmoid
    binary_mask = (mask > 0.5).astype(np.uint8)[0, 0] # Shape: [256, 256]
    
    # ── Change Reasoning ───────────────────────────────────────────────────
    # Load both images as uint8 RGB at 256×256 to match the mask
    img_a_rgb = np.array(
        Image.open(io.BytesIO(img_a_bytes)).convert('RGB').resize((256, 256)),
        dtype=np.uint8
    )
    img_b_rgb = np.array(
        Image.open(io.BytesIO(img_b_bytes)).convert('RGB').resize((256, 256)),
        dtype=np.uint8
    )
    change_regions = reason_regions(img_a_rgb, img_b_rgb, binary_mask)
    # ───────────────────────────────────────────────────────────────────────
    
    # Calculate % changed, excluding cloud interference
    cloud_area = sum(r["pixel_area"] for r in change_regions if r["change_type"] == "Possible cloud interference")
    total_changed = int(np.sum(binary_mask))
    adjusted_changed = max(0, total_changed - cloud_area)
    percent_changed = (adjusted_changed / (256 * 256)) * 100

    # Create an overlay (red for changes)
    original_img_a = Image.open(io.BytesIO(img_a_bytes)).convert('RGB').resize((256, 256))
    original_img_b = Image.open(io.BytesIO(img_b_bytes)).convert('RGB').resize((256, 256))
    overlay = np.array(original_img_b)
    overlay[binary_mask == 1] = [255, 0, 0] # Red
    
    # Blend overlay with original using PIL
    blended = Image.blend(original_img_b, Image.fromarray(overlay), alpha=0.5)
    
    # Encode all images to base64
    def _to_b64(img):
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    # Pure mask image (white on black)
    mask_img = Image.fromarray(binary_mask * 255)
    
    return {
        "percent_changed": float(percent_changed),
        "overlay_base64":  _to_b64(blended),
        "image_a_base64":  _to_b64(original_img_a),
        "image_b_base64":  _to_b64(original_img_b),
        "mask_base64":     _to_b64(mask_img),
        "change_regions":  change_regions,
    }

def spectral_change_detection(rgb_a_bytes, rgb_b_bytes, idx_a_bytes, idx_b_bytes):
    # 1. Decode images
    img_a_rgb = np.array(Image.open(io.BytesIO(rgb_a_bytes)).convert('RGB').resize((256, 256)), dtype=np.uint8)
    img_b_rgb = np.array(Image.open(io.BytesIO(rgb_b_bytes)).convert('RGB').resize((256, 256)), dtype=np.uint8)
    idx_a = np.array(Image.open(io.BytesIO(idx_a_bytes)).convert('RGB').resize((256, 256)), dtype=np.float32)
    idx_b = np.array(Image.open(io.BytesIO(idx_b_bytes)).convert('RGB').resize((256, 256)), dtype=np.float32)
    
    # 2. Extract Spectral Indices (from 0-255 back to -1 to 1)
    # Channel 0: NDVI, Channel 1: NDBI, Channel 2: SCL (0-11 scaled to 0-255)
    ndvi_a = (idx_a[:, :, 0] / 255.0 - 0.5) * 2.0
    ndvi_b = (idx_b[:, :, 0] / 255.0 - 0.5) * 2.0
    ndbi_a = (idx_a[:, :, 1] / 255.0 - 0.5) * 2.0
    ndbi_b = (idx_b[:, :, 1] / 255.0 - 0.5) * 2.0
    
    # SCL is mostly 0 to 11 (scaled to 0-255 in the PNG).
    # SCL values 8=cloud_medium, 9=cloud_high, 10=thin_cirrus, 3=cloud_shadow
    scl_a_raw = (idx_a[:, :, 2] / 255.0 * 11.0).astype(np.uint8)
    scl_b_raw = (idx_b[:, :, 2] / 255.0 * 11.0).astype(np.uint8)
    cloud_vals = {3, 8, 9, 10}
    cloud_mask_a = np.isin(scl_a_raw, list(cloud_vals))
    cloud_mask_b = np.isin(scl_b_raw, list(cloud_vals))
    cloud_mask = cloud_mask_a | cloud_mask_b
    
    diff_ndvi = ndvi_b - ndvi_a
    diff_ndbi = ndbi_b - ndbi_a
    
    # 3. Thresholding with cloud masking
    # NDBI increase > 0.1 (New buildings) OR NDVI decrease < -0.15 (Vegetation lost)
    raw_mask = ((diff_ndbi > 0.1) | (diff_ndvi < -0.15)).astype(np.uint8)
    # Zero out pixels where SCL indicates cloud/shadow
    binary_mask = (raw_mask & (~cloud_mask).astype(np.uint8))
    
    # 4. Generate Visualization
    change_regions = reason_regions(img_a_rgb, img_b_rgb, binary_mask, idx_a=idx_a, idx_b=idx_b)
    
    cloud_area = sum(r["pixel_area"] for r in change_regions if r["change_type"] == "Possible cloud interference")
    total_changed = int(np.sum(binary_mask))
    adjusted_changed = max(0, total_changed - cloud_area)
    percent_changed = (adjusted_changed / (256 * 256)) * 100
    
    # Create an overlay (red for changes)
    original_img_a = Image.open(io.BytesIO(rgb_a_bytes)).convert('RGB').resize((256, 256))
    original_img_b = Image.open(io.BytesIO(rgb_b_bytes)).convert('RGB').resize((256, 256))
    overlay = np.array(original_img_b)
    overlay[binary_mask == 1] = [255, 0, 0] # Red
    
    # Blend overlay with original using PIL
    blended = Image.blend(original_img_b, Image.fromarray(overlay), alpha=0.5)
    
    # Encode all images to base64
    def _to_b64(img):
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    mask_img = Image.fromarray(binary_mask * 255)
    
    return {
        "percent_changed": float(percent_changed),
        "overlay_base64": _to_b64(blended),
        "image_a_base64": _to_b64(original_img_a),
        "image_b_base64": _to_b64(original_img_b),
        "mask_base64":    _to_b64(mask_img),
        "change_regions": change_regions
    }

@app.post("/predict")
async def predict(image_a: UploadFile = File(...), image_b: UploadFile = File(...)):
    img_a_bytes = await image_a.read()
    img_b_bytes = await image_b.read()
    
    result = run_inference_pipeline(img_a_bytes, img_b_bytes)
    if "error" in result:
        return JSONResponse(status_code=400, content={"error": result["error"]})
        
    return JSONResponse(content=result)

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
