# Runtime image: FastAPI + ONNX Runtime, no PyTorch, no weights baked in.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ANALYSIS_DB_PATH=/app/data/analysis_history.sqlite3 \
    MODEL_ONNX_PATH=/app/model.onnx

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=10001:10001 . .
RUN mkdir -p /app/data /app/cache/osm \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R 10001:10001 /app/data /app/cache

USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# One CPU worker: ONNX model memory and free-tier RAM are the constraint.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
