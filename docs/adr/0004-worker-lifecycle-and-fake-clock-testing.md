# ADR 0004: Worker Lifecycle and FakeClock Testing

## Status
Accepted

## Context
Background workers (`SweeperWorker`, `LeakyBucketDrainWorker`) must expire idle
keys and drain leaky buckets without requiring new request traffic. They also need
predictable shutdown so tests do not leave orphaned threads.

All limiter time calculations use an injectable `Clock`, but background thread loops
still sleep on the host clock. A `FakeClock` cannot fast-forward real thread waits,
which would make fully threaded worker tests flaky or slow.

## Decision
Define a shared worker lifecycle: `start()`, `stop()`, `join(timeout=None)`,
`is_running()`, plus context-manager support. Use `MonotonicScheduler` for repeated
jobs and expose `run_pending()` and `seconds_until_next_run()` for deterministic
tests.

Drive worker behavior in tests by calling `run_pending()` with a `FakeClock`
injected into the scheduler and limiter. Reserve threaded loops with real sleeps
for integration-style checks. Mark tests that depend on thread scheduling as
`timing_dependent`.

Background loops wait on a stop event so `stop()` can interrupt sleep and shut
down cleanly.

## Consequences
- TTL sweeps and leaky-bucket drains are testable without real-time waits.
- Worker correctness is verified deterministically in the main CI subset.
- A small number of race and scheduling demos run separately as timing-dependent
  tests.
- Production-style long-running worker threads are supported, but their timing
  remains host-clock driven.
