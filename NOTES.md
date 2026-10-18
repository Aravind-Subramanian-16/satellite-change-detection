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
ONNX model is `model.onnx` (override with `MODEL_ONNX_PATH`); PyTorch training
architecture and weights are in `model.py` and `best_model.pt` (override with
`MODEL_PT_PATH`). Both files are optional until their respective pipeline runs.

## Tests and OSCD

`python3 -m pytest -q` collects only `tests/`; manual diagnostics live in
`scripts/` and never run during test collection. Tests requiring `model.onnx`
skip when it is absent. `requirements.txt` supports NumPy 2.x runtime use;
`requirements-dev.txt` additionally installs unpinned `onnx` for export.

`benchmarks/oscd_eval.py --root /content/oscd --output /path/to/results` reads
the official OSCD archive layout directly, validates every selected band against
the city-named label GeoTIFF, selects spectral thresholds and CNN preprocessing
on training cities only, then scores both CNN preprocessing variants on the
official test split. It checkpoints v2 results after every city.

In `spectral_pipeline.py`, `SpectralConfig(mode="percentile")` computes the
configured percentile separately over valid positive NDVI-drop evidence
(`-dvi`) and positive NDBI-rise evidence (`dbi`), then marks a pixel changed if
it exceeds either resulting threshold. This is an adaptive threshold on the
observed evidence distributions; it does not assume or enforce a fixed change
fraction.

## Baseline observed 2026-10-16

The host Python lacks `pytest`, so local test execution cannot yet be verified.
OSCD is not in the repository.
