from __future__ import annotations

import subprocess
from pathlib import Path


class FfmpegError(RuntimeError):
    pass


def extract_audio(input_path: Path, output_path: Path, timeout_sec: int = 120) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        str(output_path),
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise FfmpegError("ffmpeg timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise FfmpegError(f"ffmpeg failed: {exc.stderr.strip()}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise FfmpegError("Audio output missing or empty")
