from __future__ import annotations

import time
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import logging

from app.config import get_settings
from app.services.media_probe import get_duration_seconds
from app.services.whisper import WhisperError


class OpenAIWhisperError(WhisperError):
    pass


OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_MODEL = "whisper-1"
OPENAI_RESPONSE_FORMAT = "verbose_json"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DEFAULT_CHUNK_SECONDS = 120


def _run_ffmpeg(cmd: list[str], timeout_sec: int = 450) -> None:
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise OpenAIWhisperError("ffmpeg timed out during audio processing") from exc
    except subprocess.CalledProcessError as exc:
        raise OpenAIWhisperError(f"ffmpeg failed: {exc.stderr.strip()[:200]}") from exc


def _map_openai_segments(segments: Any, *, offset: float = 0.0) -> list[dict]:
    mapped: list[dict] = []
    if not isinstance(segments, list):
        return mapped
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        try:
            start = float(segment.get("start", 0.0)) + offset
            end = float(segment.get("end", 0.0)) + offset
        except (TypeError, ValueError):
            continue
        mapped.append(
            {
                "id": segment.get("id"),
                "start": start,
                "end": end,
                "text": (segment.get("text") or "").strip(),
            }
        )
    return mapped


def _transcribe_file(
    audio_path: Path,
    *,
    language: Optional[str],
    prompt: Optional[str],
    logger: logging.Logger,
) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.ORYN_WHISPER_KEY:
        raise OpenAIWhisperError("ORYN_WHISPER_KEY is not set")

    size_mb = audio_path.stat().st_size / (1024 * 1024)
    logger.info("OpenAI upload size=%.2fMB", size_mb)

    headers = {"Authorization": f"Bearer {settings.ORYN_WHISPER_KEY}"}
    data = {"model": OPENAI_MODEL, "response_format": OPENAI_RESPONSE_FORMAT}
    if language:
        data["language"] = language
    if prompt:
        data["prompt"] = prompt

    timeout = httpx.Timeout(connect=30.0, read=900.0, write=300.0, pool=30.0)
    max_retries = 4
    backoff = 1.5

    logger.info("OpenAI request response_format=%s", OPENAI_RESPONSE_FORMAT)
    for attempt in range(max_retries):
        try:
            with audio_path.open("rb") as f:
                files = {"file": (audio_path.name, f, "audio/mpeg")}
                resp = httpx.post(
                    OPENAI_TRANSCRIBE_URL,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=timeout,
                )
        except httpx.RequestError as exc:
            if attempt == max_retries - 1:
                raise OpenAIWhisperError(f"OpenAI request failed: {exc}") from exc
            sleep_for = backoff ** attempt
            logger.warning("OpenAI request error, retrying in %.1fs", sleep_for)
            time.sleep(sleep_for)
            continue

        if resp.status_code in (429, 500, 502, 503, 504):
            if attempt == max_retries - 1:
                raise OpenAIWhisperError(
                    f"OpenAI error {resp.status_code}: {resp.text[:200]}"
                )
            sleep_for = backoff ** attempt
            logger.warning(
                "OpenAI transient error %s, retrying in %.1fs",
                resp.status_code,
                sleep_for,
            )
            time.sleep(sleep_for)
            continue

        if resp.status_code >= 400:
            raise OpenAIWhisperError(
                f"OpenAI error {resp.status_code}: {resp.text[:200]}"
            )

        payload = resp.json()
        text = payload.get("text") or payload.get("transcript") or payload.get("transcriptText")
        if not text:
            raise OpenAIWhisperError("OpenAI response missing transcript text")
        return payload

    raise OpenAIWhisperError("OpenAI request failed after retries")


def _reencode_for_openai(audio_path: Path) -> Path:
    output_path = audio_path.with_suffix(".openai.mp3")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(audio_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "48k",
        str(output_path),
    ]
    _run_ffmpeg(cmd)
    return output_path


def _chunk_audio(
    audio_path: Path,
    *,
    duration: float,
    chunk_seconds: int,
    logger: logging.Logger,
) -> list[tuple[Path, float]]:
    chunks: list[tuple[Path, float]] = []
    start = 0.0
    index = 0
    while start < duration:
        chunk_path = audio_path.with_name(f"{audio_path.stem}.chunk{index}.mp3")
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{chunk_seconds:.3f}",
            "-i",
            str(audio_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "48k",
            str(chunk_path),
        ]
        logger.info("OpenAI chunking: start=%.2fs duration=%.2fs", start, chunk_seconds)
        _run_ffmpeg(cmd)
        chunks.append((chunk_path, start))
        start += chunk_seconds
        index += 1
    return chunks


def transcribe_with_openai(
    audio_path: Path,
    *,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    logger: logging.Logger | None = None,
) -> Dict[str, Any]:
    log = logger or logging.getLogger(__name__)
    upload_path = audio_path
    reencoded_path: Path | None = None
    chunk_paths: list[Path] = []
    start_time = time.monotonic()

    try:
        if upload_path.stat().st_size > MAX_UPLOAD_BYTES:
            log.warning("OpenAI audio too large, re-encoding")
            reencoded_path = _reencode_for_openai(upload_path)
            upload_path = reencoded_path

        if upload_path.stat().st_size <= MAX_UPLOAD_BYTES:
            payload = _transcribe_file(
                upload_path,
                language=language,
                prompt=prompt,
                logger=log,
            )
            segments = _map_openai_segments(payload.get("segments"))
            log.info("OpenAI segments_count=%s", len(segments))
            duration = payload.get("duration")
            elapsed = time.monotonic() - start_time
            return {
                "text": payload.get("text"),
                "segments": segments,
                "durationSeconds": duration,
                "duration": duration,
                "provider": "openai",
                "elapsed": elapsed,
            }

        duration = get_duration_seconds(upload_path, logger=log)
        if duration is None:
            duration = get_duration_seconds(audio_path, logger=log)
        if duration is None:
            raise OpenAIWhisperError("Audio too large and duration probe failed")

        chunk_info = _chunk_audio(
            upload_path,
            duration=duration,
            chunk_seconds=DEFAULT_CHUNK_SECONDS,
            logger=log,
        )
        chunk_paths = [path for path, _ in chunk_info]
        parts: list[str] = []
        all_segments: list[dict] = []
        for chunk_path, offset in chunk_info:
            payload = _transcribe_file(
                chunk_path,
                language=language,
                prompt=prompt,
                logger=log,
            )
            chunk_text = payload.get("text") or payload.get("transcript") or payload.get("transcriptText")
            if chunk_text:
                parts.append(chunk_text.strip())
            chunk_segments = _map_openai_segments(payload.get("segments"), offset=offset)
            if chunk_segments:
                all_segments.extend(chunk_segments)
        log.info("OpenAI segments_count=%s", len(all_segments))
        elapsed = time.monotonic() - start_time
        return {
            "text": " ".join(p for p in parts if p),
            "segments": all_segments,
            "durationSeconds": duration,
            "duration": duration,
            "provider": "openai",
            "elapsed": elapsed,
        }
    finally:
        if reencoded_path and reencoded_path.exists():
            try:
                reencoded_path.unlink()
            except Exception:
                pass
        for path in chunk_paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
