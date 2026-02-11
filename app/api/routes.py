from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from app.auth.dependencies import require_firebase_user
from app.jobs.enqueue import enqueue_job
from app.jobs.models import EnqueueResponse, JobStatusResponse, TranscribeRequest
from app.services.firestore import (
    build_job_doc,
    build_reel_doc,
    workspace_job_ref,
    workspace_reel_ref,
)
from app.services.hashing import sha256_hex

router = APIRouter()


@router.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "sources-api"}


@router.post("/v1/transcribe", response_model=EnqueueResponse)
def transcribe(
    payload: TranscribeRequest,
    _claims: dict = Depends(require_firebase_user),
):
    workspace_id = payload.workspaceId.strip()
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspaceId required")
    if not payload.reelUrl.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid reelUrl")

    reel_id = payload.reelId.strip() if payload.reelId else ""
    if not reel_id:
        reel_id = sha256_hex(payload.reelUrl)
    job_id = str(uuid.uuid4())

    reel_ref = workspace_reel_ref(workspace_id, reel_id)
    job_ref = workspace_job_ref(workspace_id, job_id)

    reel_snapshot = reel_ref.get()
    reel_data = reel_snapshot.to_dict() if reel_snapshot.exists else {}
    if reel_data.get("transcriptText"):
        job_ref.set(
            build_job_doc(
                {
                    "jobId": job_id,
                    "reelId": reel_id,
                    "workspaceId": workspace_id,
                    "status": "completed",
                    "source": payload.source,
                    "reelUrl": payload.reelUrl,
                }
            ),
            merge=True,
        )
        return EnqueueResponse(
            jobId=job_id, reelId=reel_id, workspaceId=workspace_id, status="completed"
        )

    reel_ref.set(
        build_reel_doc(
            {
                "reelId": reel_id,
                "workspaceId": workspace_id,
                "source": payload.source,
                "reelUrl": payload.reelUrl,
                "postedAt": payload.postedAt,
                "metadata": payload.metadata,
                "status": "queued",
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
        ),
        merge=True,
    )

    job_ref.set(
        build_job_doc(
            {
                "jobId": job_id,
                "reelId": reel_id,
                "workspaceId": workspace_id,
                "source": payload.source,
                "reelUrl": payload.reelUrl,
                "status": "queued",
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
        ),
        merge=True,
    )

    enqueue_job(job_id, workspace_id)

    return EnqueueResponse(
        jobId=job_id, reelId=reel_id, workspaceId=workspace_id, status="queued"
    )


@router.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(
    job_id: str,
    workspace_id: str = Query(..., alias="workspaceId"),
    _claims: dict = Depends(require_firebase_user),
):
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspaceId required")

    job_ref = workspace_job_ref(workspace_id, job_id)
    snapshot = job_ref.get()
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Job not found")

    data = snapshot.to_dict() or {}
    return JobStatusResponse(
        jobId=job_id,
        workspaceId=workspace_id,
        status=data.get("status", "unknown"),
        error=data.get("error"),
    )
