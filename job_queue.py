"""
FIFO job queue with limited parallelism for DownloadWorker objects.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any

from PySide6.QtCore import QObject, Signal

from worker import DownloadWorker


@dataclass
class Job:
    urls: List[str]
    opts: Dict[str, Any]
    out_dir: Path
    state: str = "Queued"          # Queued | Running | Done | Error | Cancelled
    worker: DownloadWorker | None = None


class JobQueue(QObject):
    job_updated = Signal(int)      # index whenever state/progress changes
    message     = Signal(str)      # misc log / error text
    queue_empty = Signal()

    def __init__(self, max_parallel: int = 1):
        super().__init__()
        self._max_parallel = max_parallel
        self._pending: deque[Job] = deque()
        self._running: List[Job] = []

    # ───────────────────── public API ───────────────────────────────────────
    def enqueue(self, urls: List[str], opts: Dict[str, Any], out_dir: Path):
        self._pending.append(Job(urls, opts, out_dir))
        self._launch_if_possible()

    def cancel(self, idx: int):
        jobs = self.jobs()
        if idx < 0 or idx >= len(jobs):
            return
        job = jobs[idx]
        if job.state == "Running" and job.worker:
            job.worker.terminate(); job.state = "Cancelled"
        elif job.state == "Queued":
            try: self._pending.remove(job)
            except ValueError: pass
            job.state = "Cancelled"
        self.job_updated.emit(idx)

    def jobs(self) -> List[Job]:
        return list(self._pending) + self._running

    # ───────────────────── internal helpers ────────────────────────────────
    def _launch_if_possible(self):
        while self._pending and len(self._running) < self._max_parallel:
            job = self._pending.popleft()
            worker = DownloadWorker(job.urls, job.opts)
            job.worker = worker; job.state = "Running"; self._running.append(job)
            self.job_updated.emit(self.jobs().index(job))

            worker.log_signal.connect(self.message.emit)
            worker.status_signal.connect(lambda txt, j=job: self._handle_status(j, txt))
            worker.finished.connect(lambda j=job: self._on_finished(j))
            worker.start()

    def _handle_status(self, job: Job, txt: str):
        if txt.startswith("Error"):
            job.state = "Error"
            self.message.emit(txt)
        # emit update only if job still tracked
        all_jobs = self.jobs()
        if job in all_jobs:
            self.job_updated.emit(all_jobs.index(job))

    def _on_finished(self, job: Job):
        if job.state not in ("Error", "Cancelled"):
            job.state = "Done"
        all_jobs = self.jobs()
        if job in all_jobs:
            self.job_updated.emit(all_jobs.index(job))
        if job in self._running:
            self._running.remove(job)

        if not self._pending and not self._running:
            self.queue_empty.emit()
        else:
            self._launch_if_possible()
