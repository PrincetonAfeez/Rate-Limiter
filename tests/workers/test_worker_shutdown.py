"""Test worker shutdown."""

from ratelimiter.workers.lifecycle import ManagedWorker


class OneShotWorker(ManagedWorker):
    def __init__(self) -> None:
        super().__init__(name="one-shot")

    def run(self) -> None:
        self.stop_event.wait(0.01)


def test_worker_context_manager_shutdown() -> None:
    worker = OneShotWorker()
    with worker:
        assert worker.is_running()

    assert not worker.is_running()

