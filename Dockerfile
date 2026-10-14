# ── Stage: runtime-only, ONNX inference, no PyTorch ──────────────────────────
# Base: slim Python 3.11 (smaller than 3.9-slim, better glibc for onnxruntime)
FROM python:3.11-slim

# ── System deps for opencv-python-headless (libGL, libgthread) ───────────────
# libglib2.0-0  → libgthread-2.0 required by cv2
# No X11 / display libs needed (headless only)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps — install before copying app code (layer cache) ───────────────
RUN pip install --no-cache-dir \
        fastapi==0.111.0 \
        "uvicorn[standard]==0.29.0" \
        python-multipart==0.0.9 \
        onnxruntime==1.18.0 \
        Pillow==10.3.0 \
        "numpy<2" \
        opencv-python-headless==4.9.0.80 \
        requests \
        python-dotenv \
        reportlab

# ── Application ───────────────────────────────────────────────────────────────
WORKDIR /app

# Copy only the files needed at inference time
COPY app.py            ./app.py
COPY model.onnx        ./model.onnx
COPY change_reasoner.py ./change_reasoner.py
COPY spectral_pipeline.py ./spectral_pipeline.py
COPY tiling.py ./tiling.py
COPY reports.py ./reports.py
COPY static/           ./static/

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# Single worker is enough for a demo; add --workers N for production
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
