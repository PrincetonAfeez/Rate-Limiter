# Changelog

## 0.1.4 - 2026-06-16

Full audit remediation: validation hardening, CLI parity, teaching demos, CI, and
coverage.

### Added
- Finite `cost` validation (`InvalidCostError` for NaN/Infinity).
- `InspectableLimiter` protocol; CLI uses `require_inspectable()` instead of
  `getattr` on limiter internals.
- Per-key `last_retry_after` / `last_reset_after` in metrics and `inspect` output.
- `reset --config/--name`, `simulate --hot-key`, and `demo ttl-sweeper`.
- Unsafe token-bucket race test and expanded concurrency-unsafe / failure-demo output.
- `teaching/race_explainer.py` and `concurrency/unsafe.py` compatibility re-exports.
- GitHub Actions CI, pytest-cov (80% threshold), and `docs/SCOPE.md`.
- Public exports: `LimitRule`, `load_config`, `MetricsCollector`, `SweeperWorker`,
  `InspectableLimiter`.

### Fixed
- Config `burst` rejected for fixed-window and sliding-window rules.
- `MonotonicScheduler.run_pending` reschedules jobs under `_jobs_lock`.
- Leaky bucket allowed reason standardized to `"allowed"`.
- Denied decisions logged at WARNING; negative `remaining` clamp emits a warning.
- `GlobalMetrics.total_keys` removed from dataclass (computed at snapshot time only).
- Unsafe token bucket validates `cost` via shared helper.

### Changed
- Documented sliding-window multi-window behavior, zero refill rate, and worker
  wall-clock sleep limitation in docs.
- README quickstart includes coverage and hot-key simulation.
- Scope planning files no longer gitignored.

## 0.1.3 - 2026-06-15

Audit-framework follow-ups (CLI conventions, parser test coverage, docs).

### Added
- `ratelimit --version`, single-sourced from `ratelimiter.__version__` (the
  package version is now dynamic in `pyproject.toml`).
- Parser error-path tests: malformed/empty/unknown-unit/non-positive rules and
  `load_config` missing-file / unsupported-extension cases.

### Fixed
- Runtime errors are now distinct from argparse usage errors: they print a clean
  one-line message to stderr and exit `1` (no usage dump), leaving exit `2` for
  argument-parsing errors.

### Changed
- Documented CLI exit codes (`0`/`1`/`2`) in `docs/cli.md` and the full rate-rule
  grammar (accepted units, `burst`, and algorithm aliases) in the README.

## 0.1.2 - 2026-06-15

Second audit pass: spec-conformance gaps, dead scaffolding, and input validation.

### Added
- Config files now drive real limiters: `build_limiter_from_rule` maps a parsed
  `LimitRule` (including its derived `capacity`/`refill_rate`) onto each
  algorithm, and `simulate`/`inspect` accept `--config <file> --name <limiter>`.
- `tests/integration/test_benchmark.py` actually exercises the benchmark helper
  (the previous `tests/benchmarks/benchmark_algorithms.py` was never collected by
  pytest); the benchmark file is now an honest standalone script.

### Fixed
- `failure-demo race` / `demo concurrency-unsafe` now run the same workload
  against the safe limiter and print both counts (unsafe vs safe), as the
  failure-demo spec requires.
- CLI validates `--limit` and `--period-seconds` as positive numbers, so
  `--period-seconds 0` reports a clean error instead of an uncaught
  `ZeroDivisionError`.
- `get_snapshot` now treats an expired-but-unswept record as absent, matching
  `list_keys`/`mutate_existing`.
- `MetricsCollector.snapshot()` no longer mutates collector state when computing
  `total_keys`.

### Changed
- Test fixtures (`fixtures/fake_clock.py`, `traffic_patterns.py`, `configs.py`)
  are now used by the suite instead of sitting unused (`pythonpath` includes
  `tests`).
- Removed the redundant `SweeperWorker.interval_seconds` attribute (the interval
  lives on the scheduler job). Documented oversized-`cost` behavior in
  `docs/algorithms.md` and annotated the intentionally timing-dependent
  unsafe-race test.

## 0.1.1 - 2026-06-15

Correctness and robustness pass following a full code audit.

### Fixed
- **Concurrency:** removed a lock-ordering deadlock where LRU eviction acquired
  a victim's stripe while the current request still held its own stripe.
  Eviction now runs after the key's stripe is released, so a mutation never
  holds two stripes at once. Added a contention regression test.
- **Concurrency:** the monotonic timestamp used by every algorithm is now read
  *inside* the storage lock and passed to factories/mutators, so concurrent
  requests can no longer apply time out of order.
- **Metrics:** per-key metrics are pruned when keys are expired, evicted, or
  reset, and `total_keys` now reflects currently tracked keys instead of every
  key ever seen (previously unbounded growth).
- **CLI:** `inspect` is now read-only (no longer consumes a token); `reset`
  reports the real removal result; `list` documents process-local state;
  `--threads/--keys/--requests` are validated as positive integers.
- **Algorithms:** a request whose `cost` exceeds capacity/limit now returns a
  denial with `retry_after=None` and a clear reason instead of a misleading,
  unsatisfiable retry hint.
- **Workers:** `SweeperWorker` now schedules its sweep through
  `MonotonicScheduler`; the leaky drain worker no longer resurrects keys removed
  by TTL/LRU (via `StorageBackend.mutate_existing`); context-manager exit logs a
  slow shutdown instead of raising and masking the original exception.

### Changed
- `StorageBackend.mutate` factories/mutators receive the under-lock timestamp;
  added `mutate_existing`. `DecisionMetrics`/`KeyMetrics` field renamed to
  `current_usage` for honest semantics.
- YAML config uses PyYAML when installed and otherwise a minimal parser that now
  also accepts the inline string form (matching TOML/JSON).
- Packaging: `setuptools>=77` for the SPDX license, `dev`/`yaml` optional
  extras, and the `py.typed` marker is shipped.

## 0.1.0

- Initial capstone implementation with four algorithms, in-memory storage,
  lock striping, workers, metrics, CLI demos, docs, and tests.

