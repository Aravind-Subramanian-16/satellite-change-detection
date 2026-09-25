# Satellite Image Change Detection

An end-to-end local demo web application that takes "before" and "after" satellite images, detects changes using a Siamese U-Net model trained on the LEVIR-CD dataset, and returns a highlighted mask along with a percentage of change. It includes a deterministic change-reasoning module to classify the type of change.

## 1. Project Overview & Architecture Summary

The system is built on a **MobileNetV2-based 3D Siamese U-Net** (`MobileNetV2_3D_CDNet`), drawing inspiration from FC-EF/FC-Siam architectures and AFCF3D-Net. It processes bi-temporal satellite images to produce a binary change mask. 

At inference time, the application serves an **ONNX** exported version of the PyTorch model via a **FastAPI** backend. A **Change-Reasoning Module** runs post-inference on the binary mask and original images to compute deterministic, explainable colour statistics (e.g. vegetation ratio drops, brightness uniformity, achromatic scores) to classify each changed region.

## 2. Setup Instructions

### Local Setup (Development)

1. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure API Credentials (Optional but recommended)**:
   To use the Live Sentinel-2 fetching feature, copy the example environment file and add your Copernicus Data Space Ecosystem credentials:
   ```bash
   cp .env.example .env
   ```
   *(Fill in `COPERNICUS_CLIENT_ID` and `COPERNICUS_CLIENT_SECRET` in `.env`)*

3. **Run the API and Dashboard**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
   Then open `http://localhost:8000` in your browser.

### Docker Deployment (Production)

The production Dockerfile is heavily optimized to run only the ONNX model (no PyTorch/CUDA required).

To build and run:
```bash
# 1. Build the minimal ONNX image
docker build -t cdnet-onnx:latest .

# 2. Run the container on port 8000
docker run -d --rm -p 8000:8000 --name cdnet cdnet-onnx:latest

# 3. Test the API
curl -s -X POST http://localhost:8000/predict \
  -F "image_a=@dataset/test/A/test_102_512_0.png;type=image/png" \
  -F "image_b=@dataset/test/B/test_102_512_0.png;type=image/png"
```

## 3. Final Results Table

Evaluated on the full 2,048 image LEVIR-CD test set:

| Model | Precision | Recall | F1 Score | IoU |
|---|---|---|---|---|
| STANet (Ref) | - | - | ~87.3% | ~77.4% |
| BIT (Ref) | - | - | ~89.4% | ~80.8% |
| **MobileNetV2_3D_CDNet (Ours)** | **88.82%** | **85.36%** | **87.06%** | **77.08%** |

Our lightweight MobileNetV2-based architecture achieves performance highly competitive with STANet and approaches BIT, while remaining extremely efficient for inference.

## 4. Training Details

- **Hardware:** Google Colab T4 GPU
- **Duration:** 27 epochs, total time 1.74 hours
- **Best Validation IoU:** 0.7205 (achieved on epoch 27)

## 5. Change-Reasoning Module

The `change_reasoner.py` module post-processes the model's binary mask using deterministic, explainable statistics. For every connected component (≥50 pixels) in the mask, it computes 9 colour/texture features (e.g. `veg_ratio_drop`, `uniformity_std_b`, `achromatic_score_b`) and applies a priority-chain logic to classify the change:

1. **"Likely vegetation loss / deforestation"**: Triggers if the before-image was highly vegetated (high green ratio) and saw a significant drop in vegetation index. (Highest priority)
2. **"Likely new construction"**: Triggers if the after-image becomes uniformly flat, bright, and achromatic (grey/concrete-like).
3. **"Likely bare soil / land clearing"**: Triggers if the area becomes warm-toned (high red excess) and moderately bright with low vegetation.
4. **"Change detected (type unclear)"**: Fallback for ambiguous or slight colour shifts.

## 6. Live Sentinel-2 Fetching & Spectral Change Detection

The application integrates directly with the **Copernicus Data Space Ecosystem (CDSE)** via the `/fetch-and-predict` endpoint.

**Crucial Architecture Choice (CNN vs Spectral Indices):**
While the `/predict` endpoint uses a CNN trained on 0.5m LEVIR-CD imagery, live Sentinel-2 data has a 10m spatial resolution. Running 10m imagery through a CNN expecting 0.5m structural features (buildings, cars) causes total signal loss. 

To solve this, the `/fetch-and-predict` live path **bypasses the CNN entirely**. Instead, it uses a custom Sentinel Hub Evalscript to compute **NDVI** (Normalized Difference Vegetation Index) and **NDBI** (Normalized Difference Built-up Index) directly at the source, returning them as a hidden data layer alongside the RGB image. 

The backend performs threshold-based **Spectral Differencing** on these indices (e.g., identifying severe NDVI drops paired with NDBI spikes) to generate the change mask. This ensures robust, resolution-appropriate change detection for live satellite data.

- **Smart Catalog Search**: The backend uses the CDSE Catalog API to scan a ±5 day window of the requested dates, automatically identifying and fetching the scene with the absolute lowest cloud coverage.
- **Robustness**: Includes explicit aggressive timeouts and wraps all network/authentication faults gracefully to avoid server crashes. Cloud coverage stats are returned dynamically to the frontend dashboard.

## 7. Docker Deployment & Validation

For deployment, we provide a highly optimized `Dockerfile` that packages only the ONNX runtime and FastAPI, explicitly excluding PyTorch and CUDA. 

- **Projected Image Size:** ~356 MB (uncompressed), which is roughly **7x smaller** than an equivalent PyTorch-based image (~2.5 GB).
- See [`dockerfile_report.md`](dockerfile_report.md) for a full layer-by-layer breakdown.
- *Note:* Build validation was performed via exact PyPI Linux wheel-size measurement due to a macOS/Docker Desktop version incompatibility on the development machine. The build context is kept tiny (~68 KB excluding the model) via a strict `.dockerignore` whitelist.

## 8. References

- **Dataset:** Chen, H., & Shi, Z. (2020). A Spatial-Temporal Attention-Based Method and a New Dataset for Remote Sensing Image Change Detection. *Remote Sensing*, 12(10), 1662. [DOI:10.3390/rs12101662](https://doi.org/10.3390/rs12101662)
- **FC-EF / FC-Siam:** Daudt, R. C., Le Saux, B., & Boulch, A. (2018). Fully Convolutional Siamese Networks for Change Detection. *arXiv preprint arXiv:1810.08462*.
- **AFCF3D-Net:** (3D convolution fusion concepts) *arXiv preprint arXiv:2302.05109*.
- **BIT:** Chen, H., Qi, Z., & Shi, Z. (2021). Remote Sensing Image Change Detection with Transformers. *IEEE Transactions on Geoscience and Remote Sensing*. [DOI:10.1109/TGRS.2021.3095166](https://doi.org/10.1109/TGRS.2021.3095166)
