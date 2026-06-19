"""Test lifecycle extended."""

import time

import pytest

from ratelimiter.core.errors import WorkerLifecycleError
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.workers.lifecycle import ManagedWorker


class _HangingWorker(ManagedWorker):
    def __init__(self) -> None:
        super().__init__(name="hanging", shutdown_timeout=0.05)

    def run(self) -> None:
        self.stop_event.wait(60)


class _FailWorker(ManagedWorker):
    def __init__(self, metrics: MetricsCollector) -> None:
        super().__init__(name="fail", metrics=metrics)

    def run(self) -> None:
        raise RuntimeError("worker boom")


def test_worker_start_is_idempotent_while_running() -> None:
    worker = _HangingWorker()
    worker.start()
    thread = worker._thread
    worker.start()
    assert worker._thread is thread
    worker.stop()
    worker.join(timeout=1)


def test_worker_join_noop_when_never_started() -> None:
    worker = _HangingWorker()
    worker.join(timeout=1)


def test_worker_join_raises_when_not_stopped() -> None:
    worker = _HangingWorker()
    worker.start()
    with pytest.raises(WorkerLifecycleError, match="did not stop"):
        worker.join(timeout=0.01)
    worker.stop()
    worker.join(timeout=1)


class _NeverStoppingWorker(ManagedWorker):
    def __init__(self) -> None:
        super().__init__(name="never-stop", shutdown_timeout=0.01)

    def run(self) -> None:
        while not self.stop_event.is_set():
            time.sleep(0.05)


def test_worker_context_exit_warns_on_slow_shutdown(caplog) -> None:  # type: ignore[no-untyped-def]
    worker = _NeverStoppingWorker()
    with caplog.at_level("WARNING", logger="ratelimiter.worker.never-stop"):
        with worker:
            time.sleep(0.02)
    assert any("did not stop within" in record.message for record in caplog.records)


def test_worker_records_error_when_run_raises() -> None:
    metrics = MetricsCollector()
    worker = _FailWorker(metrics)
    worker.start()
    worker.join(timeout=1)
    assert metrics.snapshot()["global"]["worker_errors"] == 1
    assert metrics.snapshot()["global"]["worker_stops"] == 1
