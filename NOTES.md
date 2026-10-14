# Repository orientation

## Pipelines and request flow

- **Pipeline A (CNN):** `app.py:run_inference_pipeline` decodes two uploads,
  normalizes them with `preprocess_image`, runs `model.onnx` through
  `onnxruntime`, thresholds its sigmoid output, and sends the mask to
  `change_reasoner.py:reason_regions`.
- **Pipeline B (live spectral):** `app.py:fetch_and_predict` resolves a place
  through `geocoding.py`, requests two Sentinel-2 L2A scenes with
  `copernicus_client.py:fetch_satellite_image`, then calls
  `app.py:spectral_change_detection`. The Copernicus Evalscript emits RGB plus
  encoded NDVI, NDBI, and SCL; the app differences NDVI/NDBI before calling
  `reason_regions`.
- The browser is served by `app.py:read_index` from `static/index.html`. It
  posts uploads to `/predict` and locations/dates to `/fetch-and-predict`.

## Local run

From this directory, install `requirements.txt`, optionally copy `.env.example`
to `.env` and supply Copernicus credentials, then run:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

`Dockerfile` is the production entry point and starts the same ASGI app. The
ONNX model is `model.onnx`; PyTorch training architecture and weights are in
`model.py` and `best_model.pt`.

## Baseline observed 2026-10-14

The host Python lacks both `pytest` and `python-dotenv`, so the baseline test
suite and app import could not run in this environment. `model.onnx` is present
(33,268,410 bytes). OSCD is not in the repository.
