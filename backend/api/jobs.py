import enum
import threading
import time
import uuid

from typing import Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import config
import pipeline


class JobStatus(enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    status: JobStatus
    created_at: float
    camera_name: str
    error: str | None = None
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status.value,
        }

        if self.status == JobStatus.COMPLETED and self.result:
            d["result"] = self.result

        if self.status == JobStatus.FAILED and self.error:
            d["error"] = self.error
        
        return d


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="job")

    def submit(self, camera_name: str) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            status=JobStatus.QUEUED,
            created_at=time.time(),
            camera_name=camera_name,
        )

        with self._lock:
            self._prune()
            self._jobs[job_id] = job
        
        self._executor.submit(self._run, job_id)

        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self, job_id: str) -> None:
        self._set_status(job_id, JobStatus.RUNNING)

        try:
            result = pipeline.run(self._jobs[job_id].camera_name) # Hangs until the job is completed

            with self._lock:
                j = self._jobs[job_id]
                j.status = JobStatus.COMPLETED
                j.result = result
        except Exception as e:
            self._set_status(job_id, JobStatus.FAILED, error=str(e))

    def _set_status(
        self, job_id: str, status: JobStatus, *, error: str | None = None
    ) -> None:
        with self._lock:
            j = self._jobs.get(job_id)
            if not j: return
            
            j.status = status
            if error is not None:
                j.error = error

    def _prune(self) -> None:
        if config.JOB_TTL_SEC <= 0:
            return
        
        cutoff = time.time() - config.JOB_TTL_SEC
        
        self._jobs = {
            jid: j for jid, j in self._jobs.items() if j.created_at > cutoff
        }
