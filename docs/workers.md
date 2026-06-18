# Workers

Workers use a common lifecycle:

```python
start()
stop()
join(timeout=None)
is_running()
```

They also support context-manager use.

`MonotonicScheduler` runs repeated jobs from monotonic time and exposes
`run_pending()` and `seconds_until_next_run()` for deterministic tests.
`SweeperWorker` reaps expired keys by registering its sweep as a job on a
`MonotonicScheduler`, so *when* to sweep is decided through the scheduler
abstraction rather than ad-hoc bookkeeping. `LeakyBucketDrainWorker` drains
known leaky bucket keys so queue depth changes are visible without new request
traffic; it updates keys in place and never recreates keys that TTL or LRU
eviction has removed.

Background loops wait on a stop event, so shutdown can interrupt sleep and
tests do not leave orphaned threads behind. The scheduler's own `run()` loop
and worker `stop_event.wait()` calls use the host's real clock, so an injected
`FakeClock` cannot fast-forward background thread sleep. Deterministic tests
drive `run_pending()` directly with a fake clock rather than running the thread
loop.

