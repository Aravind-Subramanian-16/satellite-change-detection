# Deployment

## Local setup

Create and activate a virtual environment, then install through its Python:

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

The `.env.example` values are intentionally blank. Add Copernicus Data Space
credentials to `.env` only if live imagery is needed. Never commit `.env` or put
credentials in logs.

Pipeline A loads the ONNX model lazily. The local model measured during setup is
not the verified Drive model: it is 60,534,573 bytes and fails ONNX Runtime
protobuf loading. Replace it with the Drive `oscd/weights/model.onnx` copy
(33,268,410 bytes), then confirm the input names are `input_a` and `input_b`:

```bash
python -c "import onnxruntime as o; s=o.InferenceSession('model.onnx'); print([i.name for i in s.get_inputs()])"
```

Until a valid model is present, `/health` remains available and `/predict`
returns a clear HTTP 503. The ONNX file is ignored by Git and must not be
committed. `best_model.pt` is not required by the web app.

## Render free web service

`render.yaml` defines a CPU-only Python web service on Render's free plan with
`/health` as its health check. In the Render dashboard, review the Blueprint,
configure the two Copernicus values as secrets only when needed, and deploy.
Free instances may sleep and have ephemeral storage. The model is not bundled
or downloaded by the blueprint; CNN inference therefore remains unavailable
until a compatible model is made available to the running service through a
separately managed artifact mechanism. Do not add the model or credentials to
source control.

After deployment, verify `/health`, then use a valid model before exercising
`/predict`. Live imagery additionally requires Copernicus credentials. See
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) for product limitations.
