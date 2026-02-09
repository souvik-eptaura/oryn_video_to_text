from __future__ import annotations

import os
from pathlib import Path

from google.cloud import firestore
from redis import Redis
from rq import Connection, Queue, Worker

from app.config import get_settings
from app.jobs.enqueue import enqueue_job
from app.jobs.lease import acquire_lease
from app.services.downloader import DownloadError, download_instagram
from app.services.ffmpeg import FfmpegError, extract_audio
from app.services.firestore import org_job_ref, org_reel_ref
from app.services.whisper import WhisperError, transcribe_audio
from app.utils.logging import get_logger, setup_logging
from app.utils.time import utc_now


def process_job(job_id: str, org_id: str) -> None:
    settings = get_settings()
    logger = get_logger("worker", job_id=job_id)

    job_ref = org_job_ref(org_id, job_id)
    lease_ok, info = acquire_lease(job_ref)
    if not lease_ok:
        status = info.get("status")
        if status == "leased":
            enqueue_job(job_id, org_id)
        return

    job_snapshot = job_ref.get()
    if not job_snapshot.exists:
        logger.error("Job not found")
        return

    job_data = job_snapshot.to_dict() or {}
    reel_id = job_data.get("reelId")
    reel_url = job_data.get("reelUrl")
    source = job_data.get("source", "instagram")
    attempts = int(job_data.get("attempts", 1))

    reel_ref = org_reel_ref(org_id, reel_id)
    reel_snapshot = reel_ref.get()
    reel_data = reel_snapshot.to_dict() if reel_snapshot.exists else {}

    if reel_data.get("transcriptText"):
        job_ref.update(
            {
                "status": "completed",
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "leaseUntil": utc_now(),
            }
        )
        return

    tmp_dir = Path(settings.TMP_DIR)
    video_path = tmp_dir / f"{job_id}.mp4"
    audio_path = tmp_dir / f"{job_id}.mp3"

    try:
        logger.info("Downloading video")
        download_instagram(reel_url, video_path)

        logger.info("Extracting audio")
        extract_audio(video_path, audio_path)

        logger.info("Calling Whisper")
        whisper_response = transcribe_audio(audio_path)

        transcript_text = whisper_response.get("text") or whisper_response.get("transcript")
        segments = whisper_response.get("segments")
        duration = whisper_response.get("duration") or whisper_response.get("durationSeconds")

        reel_ref.set(
            {
                "status": "new",
                "transcriptText": transcript_text,
                "transcriptSegments": segments,
                "durationSeconds": duration,
                "scrapedAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

        job_ref.update(
            {
                "status": "completed",
                "error": None,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "leaseUntil": utc_now(),
            }
        )
    except (DownloadError, FfmpegError, WhisperError, Exception) as exc:
        logger.error(f"Job failed: {exc}")
        job_ref.update(
            {
                "status": "failed",
                "error": str(exc),
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "leaseUntil": utc_now(),
            }
        )
        if attempts < settings.MAX_ATTEMPTS:
            enqueue_job(job_id, org_id)
    finally:
        for path in (video_path, audio_path):
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass


def run_worker() -> None:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    redis_conn = Redis.from_url(settings.REDIS_URL)
    with Connection(redis_conn):
        worker = Worker([Queue("sources")])
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    run_worker()
