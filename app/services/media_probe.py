from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

import logging


def get_duration_seconds(path: Path, logger: logging.Logger | None = None) -> Optional[float]:
    log = logger or logging.getLogger(__name__)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except subprocess.TimeoutExpired:
        log.warning("ffprobe timed out")
        return None
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        log.warning("ffprobe failed: %s", stderr[:200])
        return None

    try:
        payload = json.loads(result.stdout or "{}")
        duration_raw = payload.get("format", {}).get("duration")
        if duration_raw is None:
            return None
        duration = float(duration_raw)
        if duration <= 0:
            return None
        return duration
    except (ValueError, TypeError, json.JSONDecodeError):
        log.warning("ffprobe returned invalid JSON")
        return None
