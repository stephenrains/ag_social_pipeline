"""
In-memory job store + thread-pool runner.

Jobs survive only for the lifetime of the API process. If you restart the server,
in-flight jobs are lost. Good enough for local single-user usage.
"""
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .schemas import JobStatus, JobType

_MAX_WORKERS = 2  # RapidAPI is rate-limited; no point running many in parallel.


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    id: str
    type: JobType
    status: JobStatus
    params: dict[str, Any]
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["job_id"] = d.pop("id")
        return d


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="job")

    def submit(self, job_type: JobType, params: dict[str, Any], fn: Callable[[], dict[str, Any]]) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            type=job_type,
            status="queued",
            params=params,
            created_at=_now(),
        )
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run, job.id, fn)
        return job

    def _run(self, job_id: str, fn: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            j = self._jobs.get(job_id)
            if not j:
                return
            j.status = "running"
            j.started_at = _now()
        try:
            result = fn()
            with self._lock:
                j = self._jobs[job_id]
                j.status = "succeeded"
                j.result = result
                j.finished_at = _now()
        except Exception as e:
            tb = traceback.format_exc()
            with self._lock:
                j = self._jobs[job_id]
                j.status = "failed"
                j.error = f"{e}\n{tb}"
                j.finished_at = _now()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 50) -> list[Job]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]


manager = JobManager()
