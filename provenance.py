"""Reproducibility metadata attached to every analysis result and report."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_VERSION = "3.0.0"


@lru_cache(maxsize=1)
def get_commit_hash() -> str:
    """Return the deployed git commit, or an explicit marker when unavailable."""
    override = os.environ.get("GIT_COMMIT", "").strip()
    if override:
        return override
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        value = result.stdout.strip()
        if result.returncode == 0 and value:
            return value
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_provenance(
    pipeline: str,
    *,
    profile: str | None = None,
    thresholds: dict | None = None,
    scene_ids: list[str] | None = None,
    dates: dict | None = None,
    percent_masked: float | None = None,
    extra: dict | None = None,
) -> dict:
    data = {
        "commit": get_commit_hash(),
        "app_version": APP_VERSION,
        "pipeline": pipeline,
        "profile": profile,
        "thresholds": thresholds,
        "scene_ids": scene_ids or [],
        "dates": dates or {},
        "percent_masked": percent_masked,
        "timestamp_utc": utc_timestamp(),
    }
    if extra:
        data.update(extra)
    return data
