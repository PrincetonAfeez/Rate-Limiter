"""Reusable background worker lifecycle."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from types import TracebackType

from ratelimiter.core.errors import WorkerLifecycleError
from ratelimiter.observability.logging import get_logger, log_event
from ratelimiter.observability.metrics import MetricsCollector


class ManagedWorker(ABC):
    """Worker with start/stop/join and context-manager behavior."""

    def __init__(
        self,
        *,
        name: str,
        metrics: MetricsCollector | None = None,
        logger: logging.Logger | None = None,
        shutdown_timeout: float = 5.0,
    ) -> None:
        self.name = name
        self.metrics = metrics
        self.logger = logger or get_logger(f"ratelimiter.worker.{name}")
        self.shutdown_timeout = shutdown_timeout
        self._stop_event = threading.Event()
        self._lifecycle_lock = threading.RLock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_observed, name=self.name, daemon=True)
            self._thread.start()
            if self.metrics is not None:
                self.metrics.record_worker_start()
            log_event(self.logger, "worker.started", name=self.name)

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread is None:
            return
        thread.join(timeout)
        if thread.is_alive():
            raise WorkerLifecycleError(f"worker did not stop within timeout: {self.name}")

    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def __enter__(self) -> ManagedWorker:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # Do not raise on a slow shutdown here: raising inside __exit__ would
        # mask any exception that caused the block to exit. Log instead and let
        # the original exception (if any) propagate. Callers that need a hard
        # guarantee can use stop()/join() explicitly.
        self.stop()
        thread = self._thread
        if thread is not None:
            thread.join(self.shutdown_timeout)
            if thread.is_alive():
                self.logger.warning(
                    "worker %s did not stop within %.1fs of context exit",
                    self.name,
                    self.shutdown_timeout,
                )

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    def _run_observed(self) -> None:
        try:
            self.run()
        except Exception:
            if self.metrics is not None:
                self.metrics.record_worker_error()
            self.logger.exception("worker failed")
        finally:
            if self.metrics is not None:
                self.metrics.record_worker_stop()
            log_event(self.logger, "worker.stopped", name=self.name)

    @abstractmethod
    def run(self) -> None:
        """Run until stop_event is set."""

