# Phase A verification report

Date: 2026-10-21. Host: macOS 12.6 (Intel), Python 3.10.0 in `./venv`.
Server command: `./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000`.

## A1. Model status — absent, graceful failure verified

`model.onnx`, `best_model.pt` and the OSCD data are not present in this checkout.
No size or SHA-256 is reported for a file that does not exist.

```text
GET /health
{"status":"ok","model_present":false,"model_loaded":false,"commit":"bfd4bea..."}

GET /model-status
{"present":false,"path":"model.onnx","expected_bytes":33268410,
 "error":"No ONNX model at model.onnx. Set MODEL_ONNX_PATH or copy the Drive
 model.onnx (expected 33268410 bytes)."}

POST /predict (two synthetic PNGs)
HTTP 503
{"error":"Pipeline A requires an ONNX model, but model.onnx is missing. ...",
 "code":"model_unavailable", ...}
```

The file is never modified. A corrupt or wrong-size file produces an error that
includes the observed size and SHA-256 in `app.py::get_onnx_session`. Actual
size/SHA reporting remains unchecked until the owner supplies the file.

## A2. Dependencies and tests

Installed with `./venv/bin/python -m pip install -r requirements-dev.txt` after
splitting benchmark and training dependencies out of the runtime requirements
(`rasterio` is benchmark-only on this Intel macOS host; `onnx` is dev/export-only).

```text
./venv/bin/python -m pytest -q
...............................s..........
41 passed, 2 skipped, 1 warning in 4.64s
```

The skips are the Pipeline A regression test (needs `model.onnx` and a dataset
sample) and the OSCD label test (needs rasterio, benchmark-only on this host).
The warning is a Starlette deprecation notice about `httpx` in `TestClient`, not
a test failure.

Key versions: fastapi 0.156.3, starlette 1.7.0, numpy 2.2.6, onnxruntime 1.19.2,
scikit-learn 1.7.2, scipy 1.15.3, Pillow 11.3.0, playwright 1.64.0, pytest 8.4.2.

## A3. Browser verification

Playwright drove the local app in Chrome (headless). Screenshots:
`docs/screenshots/phase_a_landing.png`, `phase_a_model_error.png`,
`phase_a_dashboard.png`, `phase_a_heatmap.png`; sample PDF:
`docs/screenshots/phase_a_report_sample.pdf` (168,765 bytes, generated through
the UI's Download Report button).

| Surface | Result | Evidence |
|---|---|---|
| Landing page + map/tabs | renders | `phase_a_landing.png` |
| Upload flow without weights | clear 503 dialog, no crash | `phase_a_model_error.png`; dialog text captured in Playwright output |
| Dashboard stats/regions | renders with **synthetic injected response** | `phase_a_dashboard.png` |
| Before/after slider | present, draggable | `phase_a_dashboard.png` |
| Heatmap toggle | renders colourised confidence overlay | `phase_a_heatmap.png` |
| Report download | PDF downloaded via UI | `phase_a_report_sample.pdf`; `/report` also returned HTTP 200, 2,117 bytes for a second synthetic result |
| History | API returned the inserted synthetic row; UI uses an alert | `GET /history` → `[{"id":1,...,"percent_changed":3.2}]` |

Console: one `404` (missing favicon) and one expected `503` from `/predict`.
No page JavaScript errors. The dashboard was **not** produced by a real CNN
inference because the weights are absent; it is a UI-rendering check with a
result object explicitly labelled synthetic. Live Sentinel-2 inference is also
unverified because credentials are not configured.

## A4. Docker

Docker is not installed on this host (`docker --version` → command not found).
Image build and in-container `/health`/PDF checks are **unverified**. The
Dockerfile was still updated and linted by inspection; see the Phase E report.

## A5. Deployment files

- `.env.example` — placeholders only, no secrets.
- `render.yaml` — Docker web service, free plan, CPU only, `/health` check,
  secrets marked `sync: false`, persistent SQLite path under `/app/data`.
- `DEPLOY.md` — local, Docker and Render instructions; explains that weights are
  not baked into the image and must be provided via a persistent disk/secret.
