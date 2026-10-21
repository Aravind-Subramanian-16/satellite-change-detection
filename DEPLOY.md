# Deployment

The app is a single FastAPI process serving the dashboard and the API. The
default live path (Sentinel-2 spectral) needs no GPU and no model file. The CNN
upload path needs a valid `model.onnx`; without it `/predict` returns a clear
503 and `/health` still succeeds.

## Local

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env            # fill in the two Copernicus values if needed
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Check:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/model-status
```

The `.env.example` values are intentionally blank. Never commit `.env` or put
credentials in logs.

### Model file

An earlier local `model.onnx` measured 60,534,573 bytes and failed ONNX Runtime
protobuf loading. It is not the verified Drive copy. Replace it with the Drive
`oscd/weights/model.onnx` (33,268,410 bytes), then confirm the input names are
`input_a` and `input_b`:

```bash
python -c "import onnxruntime as o; s=o.InferenceSession('model.onnx'); print([i.name for i in s.get_inputs()])"
```

The lookup path is `MODEL_ONNX_PATH` (default `model.onnx`). If the file is
corrupt, `/model-status` reports its size, SHA-256 and the load error; replace
it, do not edit it. The ONNX file is gitignored and must not be committed.
`best_model.pt` is not required by the web app. Without a valid model,
`/health` remains available and `/predict` returns HTTP 503. The live spectral
path is unaffected.

## Docker

Docker is optional; the image runs as a non-root user and listens on 8000.

```bash
docker build -t satellite-change .
docker run -d --rm -p 8000:8000 --env-file .env \
  -v "$PWD/model.onnx:/app/model.onnx:ro" \
  -v "$PWD/data:/app/data" \
  --name satellite-change satellite-change
```

The ONNX file and PyTorch weights are excluded from the build context and are
never baked into the image. Mount them read-only when needed. `/app/data` holds
the SQLite history; `/app/cache/osm` holds road caches. Without a mounted
volume these are lost when the container is replaced.

Inside the container:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS -X POST http://127.0.0.1:8000/report \
  -H 'content-type: application/json' \
  -d '{"result":{"percent_changed":0}}' -o /tmp/report.pdf
```

If Docker is unavailable on the development machine, say so in the verification
report and mark the container checks unverified.

## Render free tier

`render.yaml` defines one Docker web service on the free plan, CPU only, with
`/health` as the health check. On Render:

1. Create a new Blueprint from this repository (or point a Web Service at the
   Dockerfile).
2. Set `COPERNICUS_CLIENT_ID` and `COPERNICUS_CLIENT_SECRET` as dashboard
   secrets. Never put them in `render.yaml`.
3. Keep one instance/worker. The free tier has 512 MB RAM, cold starts, and an
   ephemeral filesystem: SQLite history and the OSM cache reset on redeploy.
4. Do not enable a GPU; the app is CPU-only.

The model is not bundled or downloaded by the blueprint. CNN inference remains
unavailable on a fresh Render service until a compatible model is made
available through a separately managed artifact/disk mechanism. Do not add the
model or credentials to source control. Free-tier limits and availability
change; verify them on Render's official site before relying on them. No
uptime or capacity guarantee is made.

## Static hosting

There is no static-only mode: live scene search, PDF reports, history and
exports are server endpoints. Leaflet and map tiles are loaded from pinned
CDNs; Copernicus credentials stay server-side.

## Hardening and operational limits

- The app sends `X-Request-ID` (validated or generated), `X-Content-Type-Options:
  nosniff`, `X-Frame-Options: DENY`, a restrictive CSP, a referrer policy and a
  permissions policy. Responses containing analyses are `Cache-Control:
  no-store`. Access logs are one JSON object per request; credential patterns
  are redacted.
- Uploads are checked by extension, content type, byte size and decoded image
  dimensions before inference. `.npz` archives are checked for declared
  uncompressed size and pixel count. Rejections use 400/413/415 with a
  machine-readable `code`.
- `RATE_LIMIT_PER_MINUTE` is an in-process sliding window keyed by client and
  path. It resets on restart and is not shared across workers; the deployment
  target is one worker. Enforce additional limits at the proxy. Only set
  `TRUST_PROXY_HEADERS=1` when a trusted proxy overwrites `X-Forwarded-For`.
- CORS is disabled by default. `ALLOWED_ORIGINS` is an explicit comma-separated
  list; `*` is ignored and credentials are not allowed.
- There is no authentication. `/history` can expose uploaded previews, AOIs,
  filenames and results to anyone who can reach the service. Put a public
  deployment behind an authenticated reverse proxy, and restrict
  `/model-status`, `/history` and exports if that metadata is sensitive.
- Logs do not include request bodies or query strings. The app never logs
  `COPERNICUS_CLIENT_SECRET` or `COPERNICUS_CLIENT_ID`; a redaction filter
  removes common credential patterns and configured values.
- The Docker image runs as UID 10001 (non-root) and excludes tests, docs,
  benchmarks, notebooks, `.env`, weights and datasets from the build context.
  Dependency ranges in `requirements.txt` install on Colab and in the image;
  no ONNX pin is imposed.
- `.github/workflows/tests.yml` runs `python -m pytest -q` on Python 3.10 for
  pushes and pull requests. Model-dependent tests skip when weights/data are
  absent. The current local counts and skips are recorded in
  [`docs/PROGRESS.md`](docs/PROGRESS.md).

Known limitations, including the absence of authentication, history privacy,
rate-limiter scope and data licensing, are documented in
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `COPERNICUS_CLIENT_ID`, `COPERNICUS_CLIENT_SECRET` | unset | CDSE OAuth client. Missing values produce a clear 400, not a crash. |
| `MODEL_ONNX_PATH` | `model.onnx` | Optional CNN weights. |
| `MODEL_PT_PATH` | `best_model.pt` | Read-only PyTorch checkpoint for training utilities. |
| `LEARNED_MODEL_PATH` | `artifacts/learned_pixel_model.joblib` | Optional Phase D model, outside git. |
| `ENABLE_LEARNED_MODEL` | `0` | Exposes the opt-in learned endpoint. |
| `ANALYSIS_DB_PATH` | `analysis_history.sqlite3` | SQLite history. |
| `OSM_CACHE_DIR` | `cache/osm` | Overpass response cache. |
| `MAX_AOI_KM` | `10` | Maximum AOI side length. |
| `DEFAULT_WINDOW_DAYS` | `30` | ± scene search window. |
| `CLOUD_WARN_PERCENT` | `30` | SCL cloud+shadow warning threshold. |
| `MAX_ANALYSIS_PX` | `1024` | Cap on requested raster dimension. |
| `RATE_LIMIT_PER_MINUTE` | `60` | Per-IP, per-path request budget for API routes; `0` disables it. |
| `MAX_UPLOAD_MB` | `10` | Image upload cap per file. |
| `MAX_NPZ_MB` | `25` | Compressed `.npz` band-archive cap per file. |
| `MAX_REQUEST_MB` | `60` | `Content-Length` cap for JSON/multipart requests. |
| `MAX_IMAGE_PIXELS` | `25000000` | Decoded image pixel cap. |
| `MAX_IMAGE_DIMENSION` | `8000` | Decoded image side-length cap in pixels. |
| `MAX_LEARNED_PIXELS` | `4000000` | Pixel cap for the optional learned `.npz` path. |
| `MAX_NPZ_UNCOMPRESSED_MB` | `150` | Declared uncompressed-band cap for `.npz` archives. |
| `ALLOWED_ORIGINS` | empty | Comma-separated CORS origins. Empty means same-origin only; `*` is ignored. |
| `TRUST_PROXY_HEADERS` | `0` | Use the first `X-Forwarded-For` hop for rate limiting. Only behind a trusted proxy. |
| `LOG_LEVEL` | `INFO` | Log level for the app logger; access logs are structured JSON with request IDs. |

## Colab

The benchmarks and notebooks expect OSCD under `/content/oscd` and weights under
Google Drive `My Drive/oscd/weights/`. Install `requirements-benchmark.txt`
(for rasterio) and, for training, `requirements-train.txt`. See
`docs/paper/REPRODUCIBILITY.md` once generated.
