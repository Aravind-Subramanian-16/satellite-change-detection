# Satellite Image Change Detection

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Aravind-Subramanian-16/satellite-change-detection/blob/main/notebooks/oscd_benchmark.ipynb)

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

## Product features

The single-page dashboard includes upload and place search, a responsive before/after drag control, staged loading feedback, classified region cards, and downloadable result images. `GET /health` is suitable for platform health checks. `POST /report` accepts a completed result object and returns a PDF report.

Uploads larger than 256×256 are processed by overlapping 256px CNN tiles (32px overlap), then averaged during reconstruction. Live spectral requests exclude Sentinel-2 SCL cloud classes 8, 9, 10 and cloud shadow 3; `percent_cloud_masked` is returned with the result.

## Run the OSCD benchmark

The fastest way to reproduce the OSCD results is via the Colab notebook
[`notebooks/oscd_benchmark.ipynb`](notebooks/oscd_benchmark.ipynb). Before
running, place the following files in your Google Drive under
`My Drive/oscd/`:

| File | Description |
|---|---|
| `archive (1).zip` | OSCD images (from IEEE DataPort) |
| `test_labels.zip` | Official test-split ground-truth labels |
| `weights/model.onnx` | Exported ONNX model for Pipeline A CNN |
| `weights/best_model.pt` | PyTorch checkpoint for training utilities |

The notebook will raise a clear `FileNotFoundError` if any weight file is
missing.

## OSCD benchmark reproduction and v2 results

OSCD is obtained from the [official OSCD page](https://rcdaudt.github.io/oscd/) / linked IEEE DataPort download; images and weights are not committed. The dataset provides 14 train and 10 official test cities. Thresholds and the CNN preprocessing variant are selected on the 14 training cities only, before scoring the test cities.

The evaluator reads `B02`, `B03`, `B04`, `B08`, and `B11` from each acquisition, and reads labels from the city-named change-label GeoTIFF. It refuses dimension mismatches rather than resizing. Spectral configurations are selected by pooled training F1: the v2 hardcoded choice is NDVI drop `-0.30` or NDBI rise `+0.30` (both at the edge of their search grids), and percentile mode selects `99.0`. The CNN preprocessing marked chosen on train is `joint_percentile`; `reflectance` is reported as the other ablation. The saved test artifacts do not include the CNN training scores.

The main result is v2 in [`benchmarks/results/oscd_results_v2.md`](benchmarks/results/oscd_results_v2.md) and [`benchmarks/results/oscd_results_v2.json`](benchmarks/results/oscd_results_v2.json). Fractions below are percentages of pixels. Score is F1 except Otsu, where it is overall accuracy (OA).

| City | Method | True change | Predicted change | F1 (Otsu: OA) |
|---|---|---:|---:|---:|
| brasilia | Hardcoded | 2.58% | 0.32% | 0.0590 |
| brasilia | Percentile | 2.58% | 1.66% | 0.1082 |
| brasilia | Otsu | 2.58% | 69.31% | 0.3272 |
| brasilia | CNN joint-percentile (chosen on train) | 2.58% | 0.00% | 0.0000 |
| brasilia | CNN reflectance (other) | 2.58% | 0.00% | 0.0000 |
| montpellier | Hardcoded | 6.79% | 1.10% | 0.0355 |
| montpellier | Percentile | 6.79% | 1.67% | 0.0490 |
| montpellier | Otsu | 6.79% | 57.13% | 0.4514 |
| montpellier | CNN joint-percentile (chosen on train) | 6.79% | 0.00% | 0.0000 |
| montpellier | CNN reflectance (other) | 6.79% | 0.00% | 0.0000 |
| norcia | Hardcoded | 1.32% | 5.14% | 0.0350 |
| norcia | Percentile | 1.32% | 1.37% | 0.0345 |
| norcia | Otsu | 1.32% | 72.75% | 0.2850 |
| norcia | CNN joint-percentile (chosen on train) | 1.32% | 0.00% | 0.0000 |
| norcia | CNN reflectance (other) | 1.32% | 0.00% | 0.0000 |
| rio | Hardcoded | 5.69% | 2.51% | 0.1755 |
| rio | Percentile | 5.69% | 1.68% | 0.1482 |
| rio | Otsu | 5.69% | 57.09% | 0.4223 |
| rio | CNN joint-percentile (chosen on train) | 5.69% | 0.00% | 0.0000 |
| rio | CNN reflectance (other) | 5.69% | 0.00% | 0.0000 |
| saclay_w | Hardcoded | 1.14% | 9.88% | 0.0045 |
| saclay_w | Percentile | 1.14% | 1.56% | 0.0005 |
| saclay_w | Otsu | 1.14% | 48.90% | 0.5116 |
| saclay_w | CNN joint-percentile (chosen on train) | 1.14% | 0.00% | 0.0000 |
| saclay_w | CNN reflectance (other) | 1.14% | 0.00% | 0.0000 |
| valencia | Hardcoded | 0.44% | 1.69% | 0.0133 |
| valencia | Percentile | 0.44% | 1.40% | 0.0134 |
| valencia | Otsu | 0.44% | 78.25% | 0.2205 |
| valencia | CNN joint-percentile (chosen on train) | 0.44% | 0.02% | 0.0000 |
| valencia | CNN reflectance (other) | 0.44% | 0.00% | 0.0000 |
| dubai | Hardcoded | 9.92% | 0.05% | 0.0032 |
| dubai | Percentile | 9.92% | 1.72% | 0.0500 |
| dubai | Otsu | 9.92% | 79.13% | 0.2323 |
| dubai | CNN joint-percentile (chosen on train) | 9.92% | 0.00% | 0.0000 |
| dubai | CNN reflectance (other) | 9.92% | 0.00% | 0.0000 |
| lasvegas | Hardcoded | 7.67% | 0.27% | 0.0533 |
| lasvegas | Percentile | 7.67% | 1.74% | 0.1548 |
| lasvegas | Otsu | 7.67% | 80.71% | 0.2334 |
| lasvegas | CNN joint-percentile (chosen on train) | 7.67% | 0.02% | 0.0024 |
| lasvegas | CNN reflectance (other) | 7.67% | 0.00% | 0.0000 |
| milano | Hardcoded | 0.80% | 0.42% | 0.1133 |
| milano | Percentile | 0.80% | 1.72% | 0.1219 |
| milano | Otsu | 0.80% | 67.84% | 0.3252 |
| milano | CNN joint-percentile (chosen on train) | 0.80% | 0.00% | 0.0000 |
| milano | CNN reflectance (other) | 0.80% | 0.00% | 0.0000 |
| chongqing | Hardcoded | 7.21% | 1.91% | 0.3102 |
| chongqing | Percentile | 7.21% | 1.74% | 0.2481 |
| chongqing | Otsu | 7.21% | 53.58% | 0.4831 |
| chongqing | CNN joint-percentile (chosen on train) | 7.21% | 0.00% | 0.0000 |
| chongqing | CNN reflectance (other) | 7.21% | 0.00% | 0.0000 |

### Pooled v2 test results

| Method | True change | Predicted change | Reported score |
|---|---:|---:|---:|
| Hardcoded | 5.17% | 2.24% | F1 0.0782 |
| Percentile | 5.17% | 1.66% | F1 0.1176 |
| Otsu | 5.17% | 67.35% | OA 0.3439 |
| CNN joint-percentile (chosen on train) | 5.17% | 0.01% | F1 0.0007 |
| CNN reflectance (other) | 5.17% | 0.00% | F1 0.0000 |

An earlier preliminary run with a smaller search grid also scored the test split (pooled F1: percentile `0.167`, hardcoded `0.104`, Otsu `0.095`, CNN `0.0`). This is disclosed because the test split was used in that preliminary run; v2 is the main reported result, not an independent second test.

Limitations: city-level results vary widely (for example, percentile F1 ranges from `0.0005` in saclay_w to `0.2481` in chongqing). Hardcoded and percentile thresholds under-predict pooled change (`2.24%` and `1.66%`, respectively, versus `5.17%` true). Otsu labels `67.35%` of pooled pixels as changed, so its pooled OA (`0.3439`) is reported instead of its recall. OSCD provides no SCL layer here, so SCL/cloud exclusion is not measured. A domain gap between LEVIR-CD training imagery and OSCD Sentinel-2 imagery/resolution is a hypothesis that may help explain the CNN result, not an established cause. The measured selected CNN F1 is about `0.0007`; the saved results show its near-empty predictions.

**TODO:** Add published OSCD baselines with citations and comparable evaluation protocols; no baseline numbers are invented here. The v2 LaTeX versions of both tables are in [`PAPER_NOTES.md`](PAPER_NOTES.md).

## Optional learned pixel classifier (experimental)

`learned_features.py` builds 55 per-pixel features from B02/B03/B04/B08/B11/B12 on both dates: bands, five spectral indices, their differences and 3×3/7×7 local means. `benchmarks/train_pixel_classifier.py` fits a CPU `HistGradientBoostingClassifier` on 14 OSCD training cities, holding out 3 seeded training cities only to select the probability threshold. A hard guard rejects the 10 official test cities before any raster is read, and the trainer never scores the test split.

Training runs on Colab via [`notebooks/oscd_pixel_classifier.ipynb`](notebooks/oscd_pixel_classifier.ipynb); the joblib artifact is written to Drive, outside git (`*.joblib`, `artifacts/` are ignored). The artifact is **not** in this checkout, so training results are unverified here and no accuracy claim is made. The app exposes `GET /learned-model-status` and `POST /predict-learned` (two `.npz` files with the six bands). The endpoint is opt-in:

```bash
export ENABLE_LEARNED_MODEL=1
export LEARNED_MODEL_PATH=artifacts/learned_pixel_model.joblib
```

Without the flag or artifact the endpoint returns HTTP 503 and the spectral/live pipelines are unchanged. Learned results always report `display_metrics: false` and an experimental validation status; a test-city score is deferred to the preregistered Phase D2 scoring run.

## Experimental options and validation-only research

The live workflow exposes three off-by-default options: `composite_scenes` (2–3 scenes per window, temporal median of the clearest pixels), `normalise` (PIF gain/offset matching of NDVI/NDBI) and `cleanup` (3×3 morphological opening/closing plus the existing MMU). They are covered by synthetic tests, but no accuracy improvement is claimed; the v2 benchmark did not use them and OSCD supplies one pair per city.

Research-only code is not on the default path:

- `benchmarks/auto_improve.py` runs a fixed 12-system search with leave-one-city-out validation on the 14 TRAIN cities, a hard trial budget, and a checkpointed log that includes failures. It refuses official test cities. Its results are **unverified** until the owner runs [`notebooks/oscd_auto_improve.ipynb`](notebooks/oscd_auto_improve.ipynb) on Colab.
- `fusion.py` fuses spectral evidence and learned probabilities; `uncertainty.py` computes model agreement and ECE on held-out TRAIN cities; `benchmarks/finetune_cnn.py` fine-tunes a new CNN checkpoint without reading or writing `best_model.pt`/`model.onnx`.
- `docs/paper/PREREGISTRATION.md` freezes the systems, metrics and one-shot test-scoring rule. No v3 test result exists in this checkout; v2 remains the only scored test result and its earlier preliminary scoring event is disclosed above.

## Paper and audits

The manuscript and its supporting audits are in `docs/paper/`:

- [`paper.tex`](docs/paper/paper.tex) — IEEEtran manuscript (not yet compiled;
  citations are deliberate placeholders).
- [`CLAIMS_AUDIT.md`](docs/paper/CLAIMS_AUDIT.md) — claim-by-claim evidence and
  the not-claimed list.
- [`THREATS_TO_VALIDITY.md`](docs/paper/THREATS_TO_VALIDITY.md) — construct,
  internal, external, statistical, reproducibility and ethical threats.
- [`REPRODUCIBILITY.md`](docs/paper/REPRODUCIBILITY.md) — commands, hashes,
  seeds, versions and unverified items.
- [`NOVELTY_CHECKLIST.md`](docs/paper/NOVELTY_CHECKLIST.md) — shallow search
  log; status unverified, no priority claim.
- [`TODO_CITATIONS.md`](docs/paper/TODO_CITATIONS.md) — 18 unfilled citation
  slots; no invented references.
- [`VENUES.md`](docs/paper/VENUES.md) and
  [`SUBMISSION_CHECKLIST.md`](docs/paper/SUBMISSION_CHECKLIST.md) — venue
  options and submission blockers.
- [`FUTURE_WORK.md`](docs/paper/FUTURE_WORK.md) — concrete follow-up tasks.
- [`docs/presentation/slides.md`](docs/presentation/slides.md) and
  [`QA.md`](docs/presentation/QA.md) — 12-slide deck and 20 reviewer questions.

Figures and generated tables are in `docs/paper/figures/`; regenerate them
with `python scripts/make_paper_figures.py`.

## Security and limits

Uploads are limited by type, bytes and decoded dimensions; `.npz` archives also have declared-size and pixel caps. API routes use an in-process per-path rate limit, responses carry a request ID and security headers, CORS is same-origin unless `ALLOWED_ORIGINS` lists explicit origins, and access logs are structured JSON with credential redaction. There is **no authentication**: `/history` exposes stored previews, AOIs and results to anyone who can reach the service, so put public deployments behind an authenticated proxy. Rate limiting is per process and resets on restart. See [DEPLOY.md](DEPLOY.md) for variables and proxy guidance.

Intended use, validation status, privacy, licensing and operational limits are documented in [docs/LIMITATIONS.md](docs/LIMITATIONS.md). Treat every region as a candidate to verify, not a finding.

## Deployment

Build with `docker build -t satellite-change .` and run `docker run -p 8000:8000 --env-file .env satellite-change`. Supply `COPERNICUS_CLIENT_ID` and `COPERNICUS_CLIENT_SECRET` through the platform secret manager, never source control. For Render/Railway/Fly.io: select Docker deployment, expose port 8000, set the two secrets, and configure health check `/health`. Use one CPU worker because ONNX model memory and free-tier cold starts are limiting.
