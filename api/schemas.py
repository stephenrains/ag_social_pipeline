from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AccountIngestRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class PostsIngestRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    max_posts: int = Field(default=96, ge=1, le=1000)
    max_pages: int = Field(default=8, ge=1, le=50)


JobType = Literal["account", "posts"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


class JobResponse(BaseModel):
    job_id: str
    type: JobType
    status: JobStatus
    params: dict[str, Any]
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
