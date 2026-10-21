"""HTTP hardening used by app.py: limits, headers, request IDs and safe logging.

The limiter is deliberately in-process and best-effort. A single-worker
deployment is the documented target; behind a proxy the proxy should also
enforce request limits.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import time
import uuid
from collections import deque
from contextvars import ContextVar
from math import ceil, isfinite
from threading import Lock

from fastapi import Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_SECRET_WORDS = re.compile(
    r"(?i)(client[_-]?secret|client[_-]?id|authorization|access[_-]?token|refresh[_-]?token)"
    r"([\"']?\s*[:=]\s*[\"']?|\s+)([^\s,\"'&]+)"
)
_AUTH_HEADER = re.compile(r"(?i)(\bauthorization\s*[:=]\s*)(?:bearer\s+)?[^\s,\"'&]+")
_BEARER = re.compile(r"(?i)\bbearer\s+[^\s,\"'&]+")


class UploadRejected(ValueError):
    """A user upload violated a documented boundary."""

    def __init__(self, message: str, status_code: int = 400, code: str = "invalid_upload"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _env_number(name: str, fallback: float, cast=float):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return cast(fallback)
    try:
        value = cast(raw)
    except ValueError:
        return cast(fallback)
    return value if isfinite(float(value)) else cast(fallback)


def max_upload_bytes() -> int:
    return max(1, int(_env_number("MAX_UPLOAD_MB", 10) * 1024 * 1024))


def max_npz_bytes() -> int:
    return max(1, int(_env_number("MAX_NPZ_MB", 25) * 1024 * 1024))


def max_request_bytes() -> int:
    return max(1, int(_env_number("MAX_REQUEST_MB", 60) * 1024 * 1024))


def max_image_pixels() -> int:
    return max(1, int(_env_number("MAX_IMAGE_PIXELS", 25_000_000)))


def max_image_dimension() -> int:
    return max(1, int(_env_number("MAX_IMAGE_DIMENSION", 8000)))


def rate_limit_per_minute() -> int:
    return max(0, int(_env_number("RATE_LIMIT_PER_MINUTE", 60)))


def current_request_id() -> str:
    return _REQUEST_ID.get()


def reset_request_id(token) -> None:
    _REQUEST_ID.reset(token)


def set_request_id(value: str):
    return _REQUEST_ID.set(value)


def request_id_from_header(value: str | None) -> str:
    candidate = (value or "").strip()
    if _SAFE_REQUEST_ID.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


def client_identity(request: Request) -> str:
    if os.environ.get("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64] or "unknown"
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """Thread-safe per-client sliding window; every limited request counts."""

    def __init__(self, window_seconds: float = 60.0):
        self.window_seconds = float(window_seconds)
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    def check(self, identity: str, path: str, limit: int) -> float | None:
        """Return seconds to wait when the request should be rejected."""
        if limit <= 0:
            return None
        now = time.monotonic()
        cutoff = now - self.window_seconds
        key = (identity, path)
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return max(1.0, ceil(self.window_seconds - (now - hits[0])))
            hits.append(now)
            if len(self._hits) > 10_000:
                self._prune(cutoff)
        return None

    def _prune(self, cutoff: float) -> None:
        for key in list(self._hits):
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


LIMITED_PATHS = (
    "/predict",
    "/predict-learned",
    "/fetch-and-predict",
    "/scenes",
    "/timeline",
    "/geocode-suggest",
    "/report",
    "/export/",
    "/history",
)


def is_rate_limited_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in LIMITED_PATHS)


def rate_limit_response(request: Request) -> JSONResponse | None:
    limit = rate_limit_per_minute()
    if limit <= 0 or request.method == "OPTIONS" or not is_rate_limited_path(request.url.path):
        return None
    limiter: SlidingWindowLimiter = getattr(request.app.state, "rate_limiter", None) or SlidingWindowLimiter()
    if not hasattr(request.app.state, "rate_limiter"):
        request.app.state.rate_limiter = limiter
    retry_after = limiter.check(client_identity(request), request.url.path, limit)
    if retry_after is None:
        return None
    return JSONResponse(
        status_code=429,
        content={
            "error": "Too many requests. Wait before retrying.",
            "code": "rate_limited",
            "request_id": current_request_id() or None,
            "details": {"retry_after_seconds": int(retry_after), "limit_per_minute": limit},
        },
        headers={"Retry-After": str(int(retry_after))},
    )


def reset_rate_limiter(app) -> None:
    limiter = getattr(app.state, "rate_limiter", None)
    if limiter is not None:
        limiter.reset()


def request_too_large(request: Request) -> JSONResponse | None:
    if request.method not in {"POST", "PUT", "PATCH"}:
        return None
    raw = request.headers.get("content-length")
    if not raw:
        return None
    try:
        length = int(raw)
    except ValueError:
        return None
    if length <= max_request_bytes():
        return None
    return JSONResponse(
        status_code=413,
        content={
            "error": "Request body is too large.",
            "code": "request_too_large",
            "request_id": current_request_id() or None,
            "details": {"max_megabytes": round(max_request_bytes() / (1024 * 1024), 1)},
        },
    )


async def read_upload(
    upload: UploadFile,
    *,
    max_bytes: int,
    allowed_content_types: set[str],
    allowed_extensions: tuple[str, ...],
    label: str = "file",
) -> bytes:
    """Read an upload with type and byte limits, without trusting the browser."""
    filename = (upload.filename or "").lower()
    if allowed_extensions and not filename.endswith(allowed_extensions):
        raise UploadRejected(
            f"{label} must be one of: {', '.join(allowed_extensions)}.",
            status_code=415,
            code="unsupported_file_type",
        )
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in allowed_content_types | {"application/octet-stream"}:
        raise UploadRejected(
            f"{label} has unsupported content type {content_type}.",
            status_code=415,
            code="unsupported_file_type",
        )
    payload = bytearray()
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > max_bytes:
            raise UploadRejected(
                f"{label} exceeds the {max_bytes // (1024 * 1024)} MB limit.",
                status_code=413,
                code="file_too_large",
            )
    if not payload:
        raise UploadRejected(f"{label} is empty.", status_code=400, code="empty_file")
    return bytes(payload)


def validate_image_bytes(payload: bytes) -> tuple[int, int, str]:
    """Verify format and dimensions before the image is decoded into an array."""
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
            image_format = (image.format or "").upper()
    except Image.DecompressionBombError as exc:
        raise UploadRejected(
            "Image dimensions exceed the decoder safety limit.", status_code=413, code="image_too_large"
        ) from exc
    except Exception as exc:
        raise UploadRejected(
            f"Could not decode the image: {type(exc).__name__}.", status_code=400, code="invalid_image"
        ) from exc
    if image_format not in {"PNG", "JPEG"}:
        raise UploadRejected(
            f"Unsupported image format {image_format or 'unknown'}; use PNG or JPEG.",
            status_code=415,
            code="unsupported_file_type",
        )
    if width < 1 or height < 1:
        raise UploadRejected("Image has no pixels.", status_code=400, code="invalid_image")
    if width * height > max_image_pixels() or max(width, height) > max_image_dimension():
        raise UploadRejected(
            (
                f"Image is {width}x{height}; the limit is {max_image_pixels():,} pixels "
                f"and {max_image_dimension()} px per side."
            ),
            status_code=413,
            code="image_too_large",
        )
    return width, height, image_format


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob: https://cdnjs.cloudflare.com https://*.tile.openstreetmap.org; "
        "connect-src 'self'; "
        "font-src 'self' data:; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}

NO_STORE_PREFIXES = (
    "/predict",
    "/fetch-and-predict",
    "/scenes",
    "/timeline",
    "/history",
    "/report",
    "/export/",
    "/geocode-suggest",
    "/model-status",
    "/learned-model-status",
)


def apply_security_headers(response, request_id: str, path: str) -> None:
    response.headers[REQUEST_ID_HEADER] = request_id
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value
    if any(path == prefix or path.startswith(prefix) for prefix in NO_STORE_PREFIXES):
        response.headers["Cache-Control"] = "no-store"


def cors_origins() -> list[str]:
    origins = []
    for raw in os.environ.get("ALLOWED_ORIGINS", "").split(","):
        origin = raw.strip().rstrip("/")
        if origin and origin != "*" and origin not in origins:
            origins.append(origin)
    return origins


def redact_secrets(text: str) -> str:
    """Remove credential values before a log record is emitted."""
    redacted = _AUTH_HEADER.sub(r"\1[redacted]", str(text))
    redacted = _BEARER.sub("Bearer [redacted]", redacted)
    redacted = _SECRET_WORDS.sub(lambda match: f"{match.group(1)}{match.group(2)}[redacted]", redacted)
    for name in ("COPERNICUS_CLIENT_SECRET", "COPERNICUS_CLIENT_ID"):
        value = os.environ.get(name, "").strip()
        if len(value) >= 4:
            redacted = redacted.replace(value, "[redacted]")
    return redacted


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secrets(record.getMessage())
        record.args = ()
        return True


_access_logger = logging.getLogger("satellite_change.access")
_access_logger.propagate = False
if not _access_logger.handlers:
    _access_handler = logging.StreamHandler(sys.stdout)
    _access_handler.setFormatter(logging.Formatter("%(message)s"))
    _access_handler.addFilter(RedactingFilter())
    _access_logger.addHandler(_access_handler)
_access_logger.setLevel(logging.INFO)


def configure_redaction(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        if not any(isinstance(item, RedactingFilter) for item in handler.filters):
            handler.addFilter(RedactingFilter())


def log_access(
    *,
    request_id: str,
    method: str,
    path: str,
    status: int,
    duration_ms: float,
) -> None:
    _access_logger.info(
        json.dumps(
            {
                "event": "request",
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": int(status),
                "duration_ms": round(float(duration_ms), 2),
            },
            separators=(",", ":"),
        )
    )
