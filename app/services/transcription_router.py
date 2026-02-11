from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import logging
import time

from app.services.media_probe import get_duration_seconds
from app.services.openai_whisper import transcribe_with_openai
from app.services.whisper import transcribe_audio


def route_transcription(
    video_path: Path,
    audio_path: Path,
    *,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    logger: logging.Logger | None = None,
) -> Dict[str, Any]:
    log = logger or logging.getLogger(__name__)
    duration = get_duration_seconds(video_path, logger=log)
    start = time.monotonic()
    provider = "local"

    if duration is None:
        log.warning("Router decision: LOCAL duration=unknown probe_failed")
        result = transcribe_audio(audio_path)
        elapsed = time.monotonic() - start
        result.setdefault("provider", "local")
        result.setdefault("elapsed", elapsed)
        return result

    if duration < 90:
        log.info("Router decision: LOCAL duration=%.2fs", duration)
        result = transcribe_audio(audio_path)
    else:
        log.info("Router decision: OPENAI duration=%.2fs", duration)
        provider = "openai"
        result = transcribe_with_openai(
            audio_path,
            language=language,
            prompt=prompt,
            logger=log,
        )

    if duration is not None and "durationSeconds" not in result and "duration" not in result:
        result["durationSeconds"] = duration
    elapsed = time.monotonic() - start
    log.info("Transcription completed: provider=%s elapsed=%.2fs", provider, elapsed)
    result.setdefault("provider", provider)
    result.setdefault("elapsed", elapsed)
    return result
