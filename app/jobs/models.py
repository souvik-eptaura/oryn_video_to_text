from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TranscribeRequest(BaseModel):
    orgId: str = Field(..., min_length=1)
    source: str = Field(default="instagram")
    reelUrl: str = Field(..., min_length=8)
    postedAt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobStatusResponse(BaseModel):
    jobId: str
    status: str
    error: Optional[str] = None


class EnqueueResponse(BaseModel):
    jobId: str
    reelId: str
    status: str
