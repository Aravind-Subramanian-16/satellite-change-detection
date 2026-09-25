# Project Guide: Satellite Change Detection

This document provides an in-depth explanation of what has been implemented so far, the core architecture, our current results, known limitations, and the logical next steps for the project.

## 1. Implemented Modules

We have built an end-to-end local demo web application with a full ML pipeline. Here is a breakdown of the key modules:

*   **`model.py`**: Defines the PyTorch architecture, `MobileNetV2_3D_CDNet`. This is a lightweight 3D Siamese U-Net that takes bi-temporal (before and after) images and outputs a change mask.
*   **`train.py` & `evaluate.py`**: The machine learning pipeline scripts used to train the model on the LEVIR-CD dataset and evaluate its metrics (Precision, Recall, F1, IoU).
*   **`export_onnx.py`**: A utility script that converts the heavy PyTorch model (`.pt`) into an optimized ONNX format (`.onnx`) for fast, lightweight inference.
*   **`app.py`**: The FastAPI backend. It serves the web UI and provides REST endpoints (`/predict` and `/fetch-and-predict`) to process image uploads or live satellite coordinates.
*   **`change_reasoner.py`**: A deterministic post-processing module. It takes the binary change mask and original images, extracts connected components (changed regions), and analyzes colour/texture statistics to classify the *type* of change (e.g., Vegetation Loss, New Construction, Bare Soil).
*   **`copernicus_client.py`**: Integrates with the Copernicus Data Space Ecosystem (CDSE) API to fetch live Sentinel-2 satellite imagery based on bounding boxes and dates. It uses an Evalscript to retrieve RGB alongside NDVI (vegetation) and NDBI (built-up) indices.
*   **`geocoding.py`**: Provides place search and bounding box resolution so users can type a location name (e.g., "Paris") instead of raw coordinates.
*   **`Dockerfile`**: A production-ready configuration that bundles the ONNX runtime and FastAPI backend, completely stripping out heavy dependencies like PyTorch and CUDA.

## 2. System Architecture

The architecture is split into two distinct pipelines depending on the data source:

### Pipeline A: High-Resolution Local Inference (0.5m/px)
1.  **Input**: User uploads two 512x512 high-res images (e.g., from LEVIR-CD).
2.  **Inference**: The FastAPI server passes the images through the pre-compiled **ONNX model**.
3.  **Post-Processing**: The resulting binary mask is fed into the **Change Reasoner**, which assigns human-readable labels to changed areas based on colour shifts.

### Pipeline B: Live Sentinel-2 Data (10m/px)
1.  **Input**: User requests a location and date range.
2.  **Fetching**: The backend queries CDSE, automatically finding the least-cloudy image within a ±5 day window.
3.  **Crucial Bypass**: Because the CNN was trained to look for 0.5m features (like individual houses), feeding it 10m Sentinel-2 data results in noise. Therefore, this pipeline **bypasses the CNN entirely**.
4.  **Spectral Differencing**: Instead, the `copernicus_client` pulls spectral indices (NDVI/NDBI) directly from the satellite. The backend performs a mathematical threshold difference on these indices to detect changes (e.g., a drop in NDVI + spike in NDBI = likely construction).

## 3. Current Results

*   **Model Performance**: Evaluated on the LEVIR-CD test set (2,048 images), the model achieved an **IoU of 77.08%** and an **F1 Score of 87.06%**. This is highly competitive with reference models like STANet and BIT, despite being a lightweight MobileNetV2 architecture.
*   **Deployment Footprint**: By utilizing ONNX, the Docker image size is incredibly small (~356 MB), which is roughly 7x smaller than it would be if PyTorch were included.
*   **Explainability**: The deterministic change reasoner successfully provides insights into *why* a change was flagged, bridging the gap between a "black box" mask and actionable intelligence.

## 4. Known Limitations

*   **Resolution Mismatch**: The CNN is heavily overfitted to the spatial frequency of 0.5m imagery. It cannot accurately process the free 10m Sentinel-2 data. We successfully implemented Spectral Differencing as a workaround, but it lacks the structural understanding of the CNN.
*   **Static ONNX Shapes**: The exported ONNX model currently expects exactly 512x512 inputs. If a user uploads a 1024x1024 image, the current implementation might struggle without explicit tiling/sliding-window logic.
*   **Heuristic Thresholds**: The `change_reasoner.py` relies on hardcoded thresholds for colour spaces (e.g., assuming "green" implies vegetation). These thresholds might fail in different seasons (autumn leaves) or geographies (arid environments).
*   **Cloud Interference**: In the live Copernicus pipeline, clouds can cause massive false positives because they drastically alter the spectral signature of the ground.

## 5. Next Steps

Moving forward, here are the logical areas for expansion and improvement:

1.  **Tiling & Sliding Window Inference**: Update `app.py` to handle arbitrarily sized image uploads by slicing them into 512x512 tiles, running inference on each, and stitching the resulting masks back together.
2.  **Sentinel-2 CNN Training**: To unify the pipelines, we should train a separate version of the model on a 10m/px dataset (such as the OSCD - Onera Satellite Change Detection dataset). This would allow us to use Deep Learning on the live fetched data instead of relying solely on spectral indices.
3.  **Cloud Masking Integration**: Update the Copernicus Evalscript to pull the Sentinel-2 Scene Classification Layer (SCL) to explicitly mask out clouds and cloud shadows before running change detection.
4.  **Dynamic Thresholding in Reasoner**: Replace the hardcoded colour thresholds in the Change Reasoner with adaptive thresholds (e.g., Otsu's method) or K-Means clustering to better adapt to different geographies and seasons.
5.  **UI/UX Polish**: Improve the frontend dashboard to include an interactive slider for the "before/after" images, and an interactive map interface for selecting bounding boxes directly.
