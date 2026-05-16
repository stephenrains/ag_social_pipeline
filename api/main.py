"""
FastAPI app exposing the ingestion scripts as HTTP endpoints.

Run with:
    uvicorn api.main:app --reload --port 8000

All ingestion endpoints require Authorization: Bearer <API_TOKEN>.
"""
from fastapi import Depends, FastAPI, HTTPException, status

from get_ig_account_data import process_username as run_account_ingest
from get_ig_posts import process_username as run_posts_ingest

from .auth import require_token
from .jobs import manager
from .schemas import AccountIngestRequest, JobResponse, PostsIngestRequest

app = FastAPI(title="ag_social ingestion API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/ingest/account",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_token)],
)
def ingest_account(req: AccountIngestRequest) -> JobResponse:
    job = manager.submit(
        job_type="account",
        params={"username": req.username},
        fn=lambda: run_account_ingest(req.username),
    )
    return JobResponse(**job.to_dict())


@app.post(
    "/ingest/posts",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_token)],
)
def ingest_posts(req: PostsIngestRequest) -> JobResponse:
    job = manager.submit(
        job_type="posts",
        params=req.model_dump(),
        fn=lambda: run_posts_ingest(req.username, max_posts=req.max_posts, max_pages=req.max_pages),
    )
    return JobResponse(**job.to_dict())


@app.get("/jobs/{job_id}", response_model=JobResponse, dependencies=[Depends(require_token)])
def get_job(job_id: str) -> JobResponse:
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return JobResponse(**job.to_dict())


@app.get("/jobs", response_model=list[JobResponse], dependencies=[Depends(require_token)])
def list_jobs(limit: int = 50) -> list[JobResponse]:
    return [JobResponse(**j.to_dict()) for j in manager.list(limit=limit)]
