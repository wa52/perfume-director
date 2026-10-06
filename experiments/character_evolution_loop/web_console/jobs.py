from __future__ import annotations

import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(slots=True)
class Job:
    id: str
    kind: str
    character_id: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._active_by_character: dict[str, str] = {}

    def submit(
        self,
        *,
        kind: str,
        character_id: str,
        fn: Callable[[], Any],
    ) -> Job:
        with self._lock:
            active_id = self._active_by_character.get(character_id)
            if active_id:
                active = self._jobs.get(active_id)
                if active and active.status in {"queued", "running"}:
                    raise ValueError(
                        f"character {character_id!r} already has active job {active.id}"
                    )

            job = Job(
                id=uuid.uuid4().hex,
                kind=kind,
                character_id=character_id,
            )
            self._jobs[job.id] = job
            self._active_by_character[character_id] = job.id

        thread = threading.Thread(
            target=self._run,
            args=(job.id, fn),
            daemon=True,
            name=f"character-job-{job.id[:8]}",
        )
        thread.start()
        return job

    def _run(self, job_id: str, fn: Callable[[], Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = datetime.now(timezone.utc).isoformat()
        try:
            result = fn()
        except Exception as error:
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.error = f"{type(error).__name__}: {error}"
                job.result = {"traceback": traceback.format_exc(limit=8)}
                job.finished_at = datetime.now(timezone.utc).isoformat()
                self._active_by_character.pop(job.character_id, None)
        else:
            with self._lock:
                job = self._jobs[job_id]
                job.status = "succeeded"
                job.result = result
                job.finished_at = datetime.now(timezone.utc).isoformat()
                self._active_by_character.pop(job.character_id, None)

    def get(self, job_id: str) -> Job:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def active_for(self, character_id: str) -> Job | None:
        with self._lock:
            job_id = self._active_by_character.get(character_id)
            if not job_id:
                return None
            return self._jobs.get(job_id)

    def list_recent(self, limit: int = 20) -> list[Job]:
        with self._lock:
            return list(reversed(list(self._jobs.values())))[:limit]
