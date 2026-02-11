from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import httpx

from app.config import get_settings


class WhisperError(RuntimeError):
    pass


def transcribe_audio(audio_path: Path) -> Dict[str, Any]:
    settings = get_settings()

    timeout = httpx.Timeout(
        connect=30.0,
        read=900.0,
        write=300.0,
        pool=30.0,
    )

    with audio_path.open("rb") as f:
        files = {
            "file": (audio_path.name, f, "audio/mpeg")
        }

        try:
            resp = httpx.post(
                settings.WHISPER_URL,
                files=files,
                timeout=timeout,
            )
        except httpx.RequestError as exc:
            raise WhisperError(f"Whisper request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise WhisperError(
            f"Whisper error {resp.status_code}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except Exception as exc:
        raise WhisperError(
            f"Whisper returned non-JSON "
            f"(content-type={resp.headers.get('content-type')}): "
            f"{resp.text[:300]}"
        ) from exc

    text = (
        data.get("text")
        or data.get("transcript")
        or data.get("transcriptText")
    )

    if not text:
        raise WhisperError("Whisper response missing transcript text")

    return data
