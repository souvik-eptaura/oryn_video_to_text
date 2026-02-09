from __future__ import annotations

import subprocess
from pathlib import Path


class DownloadError(RuntimeError):
    pass


def download_instagram(url: str, output_path: Path, timeout_sec: int = 180) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["yt-dlp", "-o", str(output_path), url]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise DownloadError("yt-dlp timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"yt-dlp failed: {exc.stderr.strip()}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise DownloadError("Downloaded file missing or empty")
