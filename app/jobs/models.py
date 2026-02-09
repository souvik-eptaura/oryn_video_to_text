from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator


class TranscribeRequest(BaseModel):
    workspaceId: str = Field(..., min_length=1)
    source: str = Field(default="instagram")
    reelUrl: str = Field(..., min_length=8)
    postedAt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _map_org_id(cls, values: Any):
        if isinstance(values, dict):
            if "workspaceId" not in values and "orgId" in values:
                values["workspaceId"] = values["orgId"]
        return values


class JobStatusResponse(BaseModel):
    jobId: str
    workspaceId: str
    status: str
    error: Optional[str] = None


class EnqueueResponse(BaseModel):
    jobId: str
    reelId: str
    workspaceId: str
    status: str
