# Architecture Decision Record
## App — Rate Limiter
**Rate Control Systems Group | Document 1 of 5**
**Status: Accepted**

---

## Context

The Rate Control Systems group requires a reusable Python rate-limiting library and CLI for a systems-style capstone. The project must demonstrate core algorithmic trade-offs, deterministic time handling, atomic state mutation, lock striping, storage lifecycle, background workers, metrics, config-driven limiter construction, benchmark/simulation tooling, and intentional race-condition demos.

The required user-facing layer is the command-line interface. The core build intentionally has no web dashboard, no distributed store, and no Django middleware. The library remains importable as `ratelimiter`, while the installable distribution is `capstone-rate-limiter` and the console script is `ratelimit`.

The key architectural invariant is:

> Algorithms never perform read-check-write directly on raw dictionaries. They call `StorageBackend.mutate()`, which creates or reads per-key state and runs the full read/modify/write operation under the key's lock stripe.

This keeps each limiter algorithm focused on rate-limit math while the storage backend owns concurrency correctness.

---

## Decisions

### Decision 1 — Provide four algorithms behind one interface

**Chosen:** Implement token bucket, fixed window, sliding window counter, and leaky bucket behind the shared `try_acquire(key, cost=1) -> Decision` protocol.

**Rejected:** Shipping one algorithm only.

**Reason:** A capstone should compare trade-offs. Token bucket demonstrates burst/refill behavior. Fixed window demonstrates simple counters and boundary bursts. Sliding window counter demonstrates smoothing through weighted windows. Leaky bucket demonstrates queue-depth draining.

---

### Decision 2 — Return explanatory `Decision` objects

**Chosen:** Every algorithm returns a frozen `Decision` with `allowed`, `remaining`, `retry_after`, `reset_after`, `limit`, `algorithm`, and `reason`.

**Rejected:** Returning only `True` or `False`.

**Reason:** Rate limiting is operational. Callers need to know whether a request was allowed, when to retry, when the limit resets, and why a denial happened. The uniform object also powers JSON CLI output and metrics.

---

### Decision 3 — Inject a monotonic clock everywhere

**Chosen:** Algorithms, storage, and schedulers use a `Clock` protocol with `RealClock` and `FakeClock` implementations.

**Rejected:** Calling `time.time()` or `time.monotonic()` directly throughout the codebase.

**Reason:** Rate-limit behavior is time-dependent. Tests and demos need deterministic refill, window rollover, TTL expiry, and scheduler behavior without real sleeps. Monotonic time also avoids wall-clock jumps.

---

### Decision 4 — Put atomicity in `StorageBackend.mutate()`

**Chosen:** Algorithms pass a state factory and mutation function into storage. Storage reads the clock and performs the mutation inside the per-key lock.

**Rejected:** Having algorithms manually acquire locks or mutate dictionaries directly.

**Reason:** This centralizes the race-condition boundary. The safest architecture is one where algorithms cannot accidentally perform check-then-act outside the lock.

---

### Decision 5 — Use lock striping, not one global lock

**Chosen:** Map arbitrary keys to a fixed number of re-entrant lock stripes using CRC32.

**Rejected:** Using a single global lock around all state.

**Reason:** A global lock would be simple but would serialize unrelated keys. Lock striping keeps per-key atomicity while allowing unrelated keys to progress concurrently.

---

### Decision 6 — Keep the default backend in-memory and process-local

**Chosen:** `InMemoryStorage` is the default backend, with TTL, LRU eviction, safe snapshots, and memory estimates.

**Rejected:** Adding Redis or database persistence to the core build.

**Reason:** The capstone is about algorithms, concurrency, storage lifecycle, and CLI observability. A distributed store would add operational complexity and network failure modes beyond the core learning goal.

---

### Decision 7 — Expire and evict state safely

**Chosen:** Storage supports TTL expiry, sweeper-driven cleanup, LRU eviction, and metric pruning when keys disappear.

**Rejected:** Letting key state grow forever.

**Reason:** Even in-memory demo systems need bounded lifecycle behavior. TTL and max-key caps make memory behavior visible and testable.

---

### Decision 8 — Avoid deadlocks during LRU eviction

**Chosen:** Commit the current key under its stripe, release that stripe, then evict LRU keys by acquiring each victim's stripe separately.

**Rejected:** Holding one key stripe while acquiring another key's stripe.

**Reason:** Holding multiple stripes can create lock-ordering hazards. The implementation avoids deadlocks by not nesting stripe locks for unrelated keys.

---

### Decision 9 — Keep leaky bucket draining available both on-demand and as a worker

**Chosen:** `LeakyBucketLimiter` drains state during `try_acquire()` and also exposes `drain_once()` / `drain_once_all()` for `LeakyBucketDrainWorker`.

**Rejected:** Requiring a worker for correctness.

**Reason:** The limiter should make correct decisions without background threads. The worker is an operational demonstration that keeps queue-depth state updated over time.

---

### Decision 10 — Provide worker lifecycle as a reusable abstraction

**Chosen:** `ManagedWorker` provides `start()`, `stop()`, `join()`, `is_running()`, and context-manager behavior.

**Rejected:** Ad hoc thread management inside every worker.

**Reason:** Worker lifecycle is itself a systems topic. Consistent lifecycle methods make tests, demos, and shutdown behavior more reliable.

---

### Decision 11 — Use config files as real construction inputs

**Chosen:** TOML, JSON, and YAML configs parse rule strings into `LimitRule` objects and build real limiters for `simulate`, `inspect`, `reset`, and `list`.

**Rejected:** Treating config files as documentation-only.

**Reason:** Declarative config is common in real rate limiting. The project should demonstrate parsing, validation, alias normalization, and factory construction.

---

### Decision 12 — Keep YAML optional

**Chosen:** Use PyYAML when installed, otherwise support a small documented YAML subset with a built-in parser.

**Rejected:** Making YAML support a required runtime dependency.

**Reason:** The core package should remain zero-runtime-dependency. Optional extras allow a fuller YAML parser for users who want it.

---

### Decision 13 — Make unsafe race demos intentional and isolated

**Chosen:** The `teaching` package contains unsafe implementations used by demos and tests to show check-then-act races.

**Rejected:** Only showing the safe path.

**Reason:** Demonstrating the bug makes the safe architecture more meaningful. The unsafe code must be isolated and clearly labeled so it is not confused with the production path.

---

### Decision 14 — Use CLI as the primary product surface

**Chosen:** Commands include `demo`, `simulate`, `benchmark`, `inspect`, `reset`, `list`, and `failure-demo`.

**Rejected:** Building a dashboard first.

**Reason:** The README states the CLI is the required user-facing layer. CLI output is scriptable, testable, and sufficient for a systems capstone.

---

### Decision 15 — Keep distributed integrations as stretch goals

**Chosen:** Redis, asyncio integration, Django middleware, and dashboards are explicitly out of the core build.

**Rejected:** Shipping incomplete distributed features.

**Reason:** A process-local, well-tested core is better than shallow integrations. The system documents the production boundary honestly.

---

## Consequences

**Positive:**
- Algorithms are easy to compare.
- The public API is uniform.
- Deterministic tests are possible through `FakeClock`.
- Race prevention is centralized in storage.
- Lock striping allows parallelism across unrelated keys.
- TTL, LRU, metrics pruning, and workers demonstrate lifecycle management.
- The CLI can simulate hot keys, contention, cost, and throughput.
- Unsafe demos explain why atomic mutation matters.
- Runtime package stays dependency-free.

**Negative / Trade-offs:**
- State is process-local and does not persist across CLI invocations.
- No Redis or distributed coordination.
- No web dashboard or Django middleware in the core build.
- Timing-dependent race demos can be scheduler-sensitive.
- Lock striping can still serialize keys that hash to the same stripe.
- In-memory benchmarks are exploratory, not a proof of distributed correctness.
- YAML support is limited without optional PyYAML.

---

## Alternatives Not Explored

- Redis-backed distributed limiter.
- Database-backed limiter.
- Async-native limiter API.
- Django or ASGI middleware.
- HTTP API service.
- Web dashboard.
- Lua scripts or server-side atomic distributed operations.
- Token leasing across processes.
- Multi-node consistency tests.
- Prometheus/OpenTelemetry exporters.

---

*Constitution reference: Article 1 (Python fundamentals and architectural thinking), Article 3.3 (scope discipline), Article 4 (quality proportional to scope), Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity).*

---


# Technical Design Document
## App — Rate Limiter
**Rate Control Systems Group | Document 2 of 5**

---

## Overview

Rate Limiter is a CLI-first Python library that implements multiple rate-limiting algorithms over a shared atomic storage boundary.

**Distribution:** `capstone-rate-limiter`  
**Import package:** `ratelimiter`  
**Console script:** `ratelimit`  
**Python:** `>=3.11`  
**Runtime dependencies:** none  
**Optional extras:** `dev`, `yaml`, `all`  
**Version source:** `ratelimiter.__version__`

---

## System Architecture

```text
CLI / library caller
  │
  ▼
Limiter.try_acquire(key, cost)
  │
  ├── validate cost
  ├── define state factory
  ├── define mutation closure
  │
  ▼
StorageBackend.mutate(key, factory, mutator)
  │
  ├── choose key's lock stripe
  ├── read monotonic time inside lock
  ├── create or load state
  ├── run algorithm mutation
  ├── update TTL/LRU metadata
  └── return Decision + usage metrics
        │
        ▼
BaseLimiter._record_decision()
  ├── update MetricsCollector
  ├── emit structured log event
  └── return Decision
```

---

## Main Package Areas

```text
src/ratelimiter/
  __init__.py
  factory.py

  algorithms/
    base.py
    token_bucket.py
    fixed_window.py
    sliding_window_counter.py
    leaky_bucket.py

  concurrency/
    atomic.py
    locks.py

  core/
    clock.py
    config.py
    decision.py
    errors.py
    interface.py

  storage/
    base.py
    memory.py
    state.py
    ttl.py
    lru.py

  observability/
    logging.py
    metrics.py
    snapshots.py

  workers/
    lifecycle.py
    scheduler.py
    sweeper.py
    leaky_drain_worker.py

  cli/
    main.py
    commands/
      benchmark.py
      common.py
      demo.py
      failure_demo.py
      inspect.py
      list.py
      reset.py
      simulate.py

  teaching/
    race_explainer.py
    unsafe_fixed_window.py
    unsafe_token_bucket.py
```

---

## Public Data Model

### `Decision`

```python
@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    remaining: float
    retry_after: float | None
    reset_after: float | None
    limit: float
    algorithm: str
    reason: str
```

Rules:
- `retry_after` must not be negative.
- `reset_after` must not be negative.
- negative `remaining` is clamped to `0.0` and logged.
- `to_dict()` returns a JSON-friendly mapping.

---

### `LimitRule`

```python
@dataclass(frozen=True, slots=True)
class LimitRule:
    name: str
    limit: float
    period_seconds: float
    algorithm: str = "token"
    burst: float | None = None
    raw: str = ""
```

Computed properties:
- `refill_rate = limit / period_seconds`
- `capacity = burst if burst is not None else limit`

---

### `StateSnapshot`

```python
@dataclass(frozen=True, slots=True)
class StateSnapshot:
    key: str
    state_type: str
    state: dict[str, Any]
    created_at: float
    last_access: float
    expires_at: float | None
```

Used by CLI inspection and metrics-oriented tools.

---

### Stored state dataclasses

```python
TokenBucketState(tokens, last_refill, last_seen)
FixedWindowState(window_start, count, last_seen)
SlidingWindowCounterState(window_start, current_count, previous_count, last_seen)
LeakyBucketState(queue_depth, last_drained, last_seen)
StorageRecord(state, created_at, last_access, expires_at)
```

---

## Interfaces

### `RateLimiter`

```python
class RateLimiter(Protocol):
    algorithm: str

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        ...
```

---

### `InspectableLimiter`

```python
class InspectableLimiter(RateLimiter, Protocol):
    storage: StorageBackend
    metrics: MetricsCollector
```

Used by CLI commands that need snapshots, resets, active keys, or memory estimates.

---

### `StorageBackend`

Required methods:
- `mutate(key, factory, mutator)`
- `mutate_existing(key, mutator)`
- `get_snapshot(key)`
- `snapshot()`
- `reset(key)`
- `list_keys()`
- `expire(now=None)`
- `estimate_memory_bytes()`

Important invariant:
- factory and mutator receive monotonic time read inside the lock.

---

## Algorithms

### Token Bucket

Parameters:
- `capacity`
- `refill_rate`

State:
- `tokens`
- `last_refill`
- `last_seen`

Algorithm:
```text
elapsed = now - last_refill
tokens = min(capacity, tokens + elapsed * refill_rate)
if cost <= tokens:
    tokens -= cost
    allow
else:
    deny
```

Strengths:
- allows bursts up to capacity
- smooth refill over time
- good default for API-style rate limiting

Trade-offs:
- unused capacity accumulates to burst limit
- cost greater than capacity can never succeed

---

### Fixed Window

Parameters:
- `limit`
- `window_seconds`

State:
- `window_start`
- `count`
- `last_seen`

Algorithm:
```text
current_window = floor(now / window_seconds) * window_seconds
if stored window_start != current_window:
    reset count
if count + cost <= limit:
    count += cost
    allow
else:
    deny until window reset
```

Strengths:
- simple and fast
- easy to explain

Trade-offs:
- boundary bursts can admit up to roughly 2x limit around a window edge

---

### Sliding Window Counter

Parameters:
- `limit`
- `window_seconds`

State:
- `window_start`
- `current_count`
- `previous_count`
- `last_seen`

Algorithm:
```text
roll current window if needed
weight = (window_seconds - elapsed_in_current_window) / window_seconds
estimate = current_count + previous_count * weight
if estimate + cost <= limit:
    current_count += cost
    allow
else:
    deny
```

Strengths:
- smooths fixed-window boundary bursts
- cheaper than storing every timestamp

Trade-offs:
- approximate, not exact sliding log behavior

---

### Leaky Bucket

Parameters:
- `capacity`
- `drain_rate`

State:
- `queue_depth`
- `last_drained`
- `last_seen`

Algorithm:
```text
elapsed = now - last_drained
queue_depth = max(0, queue_depth - elapsed * drain_rate)
if queue_depth + cost <= capacity:
    queue_depth += cost
    allow
else:
    deny until enough queue drains
```

Strengths:
- models steady outflow
- supports autonomous drain worker

Trade-offs:
- queue-depth semantics differ from token bucket semantics
- needs careful explanation when used for API admission control

---

## Storage and Concurrency

### Lock striping

`LockManager` creates a fixed tuple of `threading.RLock` objects. A key maps to a stripe with:

```text
crc32(key.encode("utf-8")) % stripe_count
```

This provides:
- atomicity for the same key
- concurrent progress for unrelated keys that land on different stripes
- deterministic stripe assignment

---

### In-memory mutation flow

```text
mutate(key, factory, mutator)
  stripe = lock_for(key)
  with stripe:
      now = clock.now()
      record = create_or_load_record(key, factory, now)
      result = mutator(record.state, now)
      update last_access / expires_at
  evict_lru(exclude_key=key)
  return result
```

Key detail:
- LRU eviction happens after releasing the current key stripe to avoid lock-order deadlocks.

---

### TTL expiry

Records store `expires_at`. Expired records are treated as absent by:
- mutation
- `mutate_existing`
- `get_snapshot`
- `list_keys`
- sweeper-driven `expire`

Metrics for removed keys are pruned so per-key metrics remain bounded.

---

### LRU eviction

When `max_keys` is configured:
- storage chooses least recently used victims
- it avoids evicting the current key when possible
- it acquires the victim stripe before deleting
- it prunes metrics and records eviction counters

---

## Time Model

### `RealClock`

Uses:
- `time.monotonic()`
- `time.sleep()`

### `FakeClock`

Supports:
- `now()`
- `advance(seconds)`
- `set(value)`
- `sleep(seconds)` as deterministic time advancement

Rules:
- fake time cannot move backward
- used heavily in tests and demos

---

## Workers

### `ManagedWorker`

Lifecycle:
- `start()`
- `stop()`
- `join(timeout=None)`
- `is_running()`
- context manager entry/exit

Behavior:
- records worker starts/stops/errors in metrics
- logs lifecycle events
- avoids masking block exceptions during context-manager exit

---

### `MonotonicScheduler`

Schedules repeated jobs by monotonic time.

Important testing note:
- worker thread waits on the host clock
- tests can drive fake-time schedules by calling `run_pending()` directly

---

### `SweeperWorker`

Purpose:
- periodically call `storage.expire()` to remove idle keys without requiring new traffic

Behavior:
- sweeps once immediately on startup
- then uses `MonotonicScheduler`

---

### `LeakyBucketDrainWorker`

Purpose:
- periodically call `limiter.drain_once_all()` for known leaky bucket keys

Behavior:
- logs drain events when keys are drained
- uses regular worker lifecycle

---

## Observability

### Per-key metrics

Tracked fields:
- allowed count
- denied count
- denial rate
- current usage
- queue depth
- last decision time
- last denial reason
- last retry-after
- last reset-after

### Global metrics

Tracked fields:
- total allowed
- total denied
- evicted key count
- expired key count
- worker starts/stops/errors
- approximate memory bytes
- total active metric keys

### Logs

Structured JSON-like events include:
- per-decision events
- storage expiry/eviction events
- worker lifecycle events
- scheduler job execution
- benchmark summary events

Allowed decisions log at INFO. Denied decisions log at WARNING.

---

## CLI Command Flow

```text
ratelimit <command>
  │
  ├── demo
  ├── simulate
  ├── benchmark
  ├── inspect
  ├── reset
  ├── list
  └── failure-demo
```

Runtime errors from `RateLimiterError` and `ValueError` return exit code `1`. Argparse usage errors remain exit code `2`.

---

## Configuration

Supported formats:
- TOML
- JSON
- YAML / YML

Rule grammar:
```text
<limit>/<unit> [burst <n>] [algorithm <name>]
```

Units:
- seconds: `s`, `sec`, `second`, `seconds`
- minutes: `m`, `min`, `minute`, `minutes`
- hours: `h`, `hr`, `hour`, `hours`

Algorithm aliases normalize to:
- `token`
- `fixed-window`
- `sliding-window-counter`
- `leaky`

`burst` is only valid for token and leaky algorithms.

---

## Known Limits

- Process-local in-memory state.
- No persistent shared backend.
- No Redis or database adapter in the core build.
- No web dashboard.
- No Django middleware.
- No async-native limiter API.
- CLI `inspect` / `reset` / `list` create fresh limiters, so state does not persist between invocations.
- Benchmark results are exploratory and machine-dependent.
- Timing-dependent race demos depend on scheduler timing.

---

## Verification Summary

The repository configures:
- pytest test suite under `tests`
- strict mypy over `ratelimiter`
- coverage source `ratelimiter`
- coverage fail-under 95
- timing-dependent pytest marker
- CI-safe subset excluding timing-dependent tests
- separate timing-dependent race-test CI job
- Python 3.11 and 3.12 CI matrix

---

*Constitution reference: Article 4 (engineering quality), Article 6 (behavior verification), Article 7 (progressive complexity), and Article 8 (valid learner work).*

---


# Interface Design Specification
## App — Rate Limiter
**Rate Control Systems Group | Document 3 of 5**

---

## Public Python API

### Basic import

```python
from ratelimiter import TokenBucketLimiter, FakeClock

clock = FakeClock()
limiter = TokenBucketLimiter(capacity=3, refill_rate=1, clock=clock)
decision = limiter.try_acquire("user-123")
```

---

### Public exports

Top-level exports include:
- `Decision`
- `FakeClock`
- `RealClock`
- `TokenBucketLimiter`
- `FixedWindowLimiter`
- `SlidingWindowCounterLimiter`
- `LeakyBucketLimiter`
- `InMemoryStorage`
- `LimitRule`
- `RateLimiterConfig`
- `load_config`
- `ConfigError`
- `RateLimiter`
- `InspectableLimiter`
- `MetricsCollector`
- `SweeperWorker`
- `LeakyBucketDrainWorker`
- `build_limiter`
- `build_limiter_from_rule`
- `rule_from_config`
- `require_inspectable`

---

## Shared limiter contract

```python
try_acquire(key: str, cost: int | float = 1) -> Decision
```

Rules:
- `key` is an arbitrary string.
- `cost` must be finite and positive.
- all algorithms return `Decision`.
- denied decisions include a reason.
- `retry_after` and `reset_after` are never negative.

---

## Algorithm constructors

### Token bucket

```python
TokenBucketLimiter(
    capacity=20,
    refill_rate=10,
    clock=None,
    storage=None,
    metrics=None,
    ttl_seconds=None,
    max_keys=None,
)
```

Meaning:
- capacity = burst size
- refill_rate = tokens per second

---

### Fixed window

```python
FixedWindowLimiter(
    limit=100,
    window_seconds=60,
    clock=None,
    storage=None,
    metrics=None,
    ttl_seconds=None,
    max_keys=None,
)
```

---

### Sliding window counter

```python
SlidingWindowCounterLimiter(
    limit=100,
    window_seconds=60,
    clock=None,
    storage=None,
    metrics=None,
    ttl_seconds=None,
    max_keys=None,
)
```

---

### Leaky bucket

```python
LeakyBucketLimiter(
    capacity=40,
    drain_rate=20,
    clock=None,
    storage=None,
    metrics=None,
    ttl_seconds=None,
    max_keys=None,
)
```

Additional methods:
- `drain_once(key) -> float`
- `drain_once_all() -> dict[str, float]`

---

## Factory interface

### Build from flags

```python
from ratelimiter import build_limiter

limiter = build_limiter(
    "token",
    limit=10,
    period_seconds=1,
    burst=20,
)
```

### Build from parsed rule

```python
from ratelimiter import build_limiter_from_rule, load_config

config = load_config("configs/sample_limits.toml")
rule = config.rules["api"]
limiter = build_limiter_from_rule(rule)
```

### Select rule from config

```python
from ratelimiter import rule_from_config

rule = rule_from_config("configs/sample_limits.toml", "login")
```

---

## Config file interface

### TOML

```toml
[limiters.api]
rule = "10/sec burst 20 algorithm token"

[limiters.login]
rule = "50/min algorithm sliding-window-counter"
```

### JSON

```json
{
  "limiters": {
    "api": {"rule": "10/sec burst 20 algorithm token"},
    "login": {"rule": "50/min algorithm sliding-window-counter"}
  }
}
```

### YAML

```yaml
limiters:
  api:
    rule: "10/sec burst 20 algorithm token"
  login: "50/min algorithm sliding-window-counter"
```

---

## Rule grammar

```text
<limit>/<unit> [burst <n>] [algorithm <name>]
```

Examples:
```text
100/min
10/sec burst 20
100/hour algorithm fixed-window
50/min algorithm sliding-window-counter
20/sec burst 40 algorithm leaky
```

Validation:
- limit must be positive
- unit must be recognized
- burst must be positive
- burst is valid only for `token` and `leaky`
- algorithm must normalize to a supported algorithm

---

## CLI Interface

### Console script

```powershell
ratelimit <command> [options]
```

### Version

```powershell
ratelimit --version
```

---

## CLI Commands

### `demo`

```powershell
ratelimit demo all
ratelimit demo token-bucket-burst
ratelimit demo fixed-window-boundary
ratelimit demo sliding-window-counter
ratelimit demo leaky-bucket-drain
ratelimit demo ttl-sweeper
ratelimit demo concurrency-safe
ratelimit demo concurrency-unsafe
```

Purpose:
- scripted demonstrations with human-readable lines

---

### `simulate`

```powershell
ratelimit simulate --algorithm token --keys 100 --requests 10000 --threads 8
ratelimit simulate --algorithm token --hot-key --requests 5000 --threads 16
ratelimit simulate --algorithm token --cost 2 --limit 10 --requests 100
ratelimit simulate --config configs/sample_limits.toml --name api --requests 1000
```

Options:
- `--algorithm`
- `--keys`
- `--requests`
- `--threads`
- `--limit`
- `--period-seconds`
- `--burst`
- `--config`
- `--name`
- `--hot-key`
- `--cost`

Output includes:
- allowed
- denied
- requests
- threads
- keys
- cost
- elapsed seconds
- throughput per second
- global metrics
- approximate memory bytes
- active keys touched during the run
- hot-key flag

---

### `benchmark`

```powershell
ratelimit benchmark --algorithms token,fixed,sliding,leaky --keys 1000 --threads 16 --cost 1
```

Options:
- `--algorithms`
- `--keys`
- `--threads`
- `--requests`
- `--limit`
- `--period-seconds`
- `--cost`

Behavior:
- builds each algorithm
- runs the same synthetic threaded traffic pattern
- reports throughput and memory estimates
- logs a structured `benchmark.summary` event

---

### `inspect`

```powershell
ratelimit inspect user-123 --algorithm token
ratelimit inspect user-123 --config configs/sample_limits.toml --name login
```

Behavior:
- builds a fresh process-local limiter
- reads snapshot and metrics for the key
- does not mutate the key

Important note:
- fresh CLI invocations do not see state from previous CLI invocations.

---

### `reset`

```powershell
ratelimit reset user-123 --algorithm token
ratelimit reset user-123 --config configs/sample_limits.toml --name login
```

Behavior:
- builds a fresh limiter
- attempts to remove the key
- reports `reset: true|false`

Important note:
- with the default in-memory backend, reset is useful inside the same process/library usage; across CLI invocations there is usually no persisted state to reset.

---

### `list`

```powershell
ratelimit list
ratelimit list --config configs/sample_limits.yaml
```

Behavior:
- lists configured limiter rules
- returns empty `active_keys` for fresh CLI state
- includes an explanation that process-local state does not persist across invocations

---

### `failure-demo`

```powershell
ratelimit failure-demo race
```

Behavior:
- prints a check-then-act race timeline
- runs unsafe vs safe concurrency comparison
- explains why `StorageBackend.mutate()` fixes over-admission

---

## CLI Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Success |
| `1` | Runtime rate-limiter/config/value error |
| `2` | argparse usage error |

---

## Side Effects

| Operation | Side effect |
|---|---|
| `try_acquire` | May create/update key state and metrics |
| denied decision | WARNING log event |
| allowed decision | INFO log event |
| `storage.reset` | Deletes key state and metrics |
| `storage.expire` | Removes expired keys and records expiry metric |
| LRU eviction | Deletes old keys and records eviction metric |
| `SweeperWorker` | Expires idle keys periodically |
| `LeakyBucketDrainWorker` | Drains leaky bucket state periodically |
| CLI `simulate` | Builds fresh in-memory limiter and emits JSON |
| CLI `benchmark` | Runs threaded synthetic traffic and logs summary |

---

## Error Contract

Library errors derive from the project error hierarchy. CLI catches `RateLimiterError` and `ValueError`, prints:

```text
ratelimit: error: <message>
```

and exits with code `1`.

Argparse validation errors print usage and exit with code `2`.

---

*Constitution reference: Article 4 (input/output boundaries), Article 6 (verification), and Article 8 (understandable and verifiable work).*

---


# Runbook
## App — Rate Limiter
**Rate Control Systems Group | Document 4 of 5**

---

## Requirements

### Runtime

- Python 3.11+
- no required third-party dependencies

### Optional

- PyYAML for full YAML support

### Development

- pytest
- pytest-cov
- mypy

---

## Installation

### Core runtime

```powershell
python -m pip install -e .
```

### Development tools

```powershell
python -m pip install -e ".[dev]"
```

### YAML support

```powershell
python -m pip install -e ".[yaml]"
```

### Everything

```powershell
python -m pip install -e ".[all]"
```

### Requirements file path

```powershell
python -m pip install -r requirements-dev.txt
```

### Without install

```powershell
$env:PYTHONPATH = "src"
python -m ratelimiter.cli.main demo all
```

Linux/macOS:

```bash
PYTHONPATH=src python -m ratelimiter.cli.main demo all
```

---

## First Smoke Tests

```powershell
ratelimit --version
ratelimit demo token-bucket-burst
ratelimit simulate --algorithm token --keys 10 --requests 100 --threads 4
```

Expected:
- version prints successfully
- demo prints readable decisions
- simulation prints JSON with allowed/denied totals

---

## Standard Operating Procedures

### Run all demos

```powershell
ratelimit demo all
```

Use this for capstone walkthroughs.

---

### Demonstrate fixed-window boundary burst

```powershell
ratelimit demo fixed-window-boundary
```

Expected:
- shows requests admitted around the window boundary
- explains why fixed windows can burst

---

### Demonstrate safe concurrency

```powershell
ratelimit demo concurrency-safe
```

Expected:
- actual allowed never exceeds capacity
- proves atomic mutation behavior

---

### Demonstrate unsafe race condition

```powershell
ratelimit failure-demo race
```

Expected:
- prints timeline of two threads reading stale state
- compares unsafe and safe limiters

---

### Simulate many keys

```powershell
ratelimit simulate --algorithm token --keys 100 --requests 10000 --threads 8
```

Expected:
- JSON output with throughput and active keys

---

### Simulate hot-key contention

```powershell
ratelimit simulate --algorithm token --hot-key --requests 5000 --threads 16
```

Expected:
- higher contention on one lock stripe/key
- useful for concurrency discussion

---

### Simulate weighted cost

```powershell
ratelimit simulate --algorithm token --cost 2 --limit 10 --requests 100
```

Expected:
- each request consumes 2 capacity units

---

### Benchmark algorithms

```powershell
ratelimit benchmark --algorithms token,fixed,sliding,leaky --keys 1000 --threads 16 --cost 1
```

Expected:
- one JSON row per algorithm
- throughput and approximate memory estimates

---

### Use config file

```powershell
ratelimit simulate --config configs/sample_limits.toml --name api --requests 1000
ratelimit list --config configs/sample_limits.json
ratelimit list --config configs/sample_limits.yaml
```

Expected:
- config rules parse into real limiter instances

---

### Inspect and reset

```powershell
ratelimit inspect user-123 --config configs/sample_limits.toml --name login
ratelimit reset user-123 --config configs/sample_limits.toml --name login
```

Expected:
- with fresh CLI invocation, key is usually inactive because state is process-local
- use the library API for persistent inspection within one Python process

---

## Library Smoke Test

```python
from ratelimiter import FakeClock, TokenBucketLimiter

clock = FakeClock()
limiter = TokenBucketLimiter(capacity=3, refill_rate=1, clock=clock)
print(limiter.try_acquire("user").to_dict())
clock.advance(1.0)
print(limiter.try_acquire("user").to_dict())
```

Expected:
- deterministic token refill without real sleep

---

## Worker Smoke Test

```python
from ratelimiter import FakeClock, SweeperWorker, TokenBucketLimiter, require_inspectable

clock = FakeClock()
limiter = TokenBucketLimiter(capacity=1, refill_rate=1, clock=clock, ttl_seconds=5)
internals = require_inspectable(limiter)
limiter.try_acquire("idle")
clock.advance(6)
removed = internals.storage.expire()
print(removed)
```

Expected:
- expired key removed

---

## Quality Checks

### Full test suite

```powershell
pytest
```

### Coverage

```powershell
pytest --cov=ratelimiter --cov-report=term-missing
```

Coverage gate:
```text
95%
```

### CI-safe subset

```powershell
pytest -m "not timing_dependent" --cov=ratelimiter --cov-report=term-missing
```

### Timing-dependent race demos

```powershell
pytest -m timing_dependent
```

### Type check

```powershell
mypy src
```

---

## CI Parity

GitHub Actions runs:
- Python 3.11 and 3.12
- install package with dev and YAML extras
- pytest excluding timing-dependent tests with coverage
- mypy over `src`
- separate timing-dependent race-test job on Python 3.12

---

## Health Checks

### Verify package import

```powershell
python -c "from ratelimiter import TokenBucketLimiter, Decision; print('ok')"
```

Expected:
```text
ok
```

---

### Verify CLI

```powershell
ratelimit demo all
```

Expected:
- human-readable demo output
- exit code 0

---

### Verify config parser

```powershell
ratelimit list --config configs/sample_limits.toml
```

Expected:
- JSON listing configured limiter names

---

### Verify hot-key safety

```powershell
ratelimit demo concurrency-safe
```

Expected:
- allowed count does not exceed expected maximum

---

## Expected Failure Modes

### Invalid cost

Cause:
- cost is zero, negative, NaN, or infinite

Expected:
- `InvalidCostError` in library
- CLI prints clean error and exits 1

---

### Invalid limit

Cause:
- capacity, limit, window, TTL, or max_keys is invalid

Expected:
- `InvalidLimitError`

---

### Invalid config rule

Examples:
```text
10/fortnight
10/sec burst 20 algorithm fixed-window
10/sec algorithm unknown
```

Expected:
- `ConfigError`

---

### YAML parser limitation

Cause:
- YAML file uses syntax outside the built-in minimal parser and PyYAML is not installed

Fix:
```powershell
python -m pip install -e ".[yaml]"
```

---

### CLI inspect shows inactive key after simulate

Cause:
- each CLI invocation creates a fresh in-memory limiter

Fix:
- use library API in one Python process
- add shared backend as a future enhancement

---

### Timing-dependent test flakes

Cause:
- intentional race demos rely on thread scheduling

Fix:
- run CI-safe subset for normal gate
- run timing-dependent tests separately

---

## Troubleshooting Decision Tree

```text
CLI command failed
  ├── argparse usage error?
  │     └── check required command and positive numeric flags
  ├── ConfigError?
  │     ├── validate rule grammar
  │     ├── validate algorithm aliases
  │     └── remove burst from fixed/sliding rules
  ├── inspect/reset shows no key?
  │     └── remember state is process-local per invocation
  ├── race demo inconsistent?
  │     └── rerun timing-dependent demo; it depends on scheduler timing
  └── YAML failed?
        └── install .[yaml] or use documented minimal subset

Library behavior unexpected
  ├── denied too soon?
  │     ├── check cost
  │     ├── check burst/capacity
  │     └── check fake-clock advancement
  ├── retry_after is None?
  │     └── cost may exceed capacity/limit or refill rate is zero
  ├── key expired?
  │     └── inspect ttl_seconds and clock time
  └── many keys disappeared?
        └── check max_keys LRU eviction
```

---

## Maintenance Notes

- Keep `StorageBackend.mutate()` as the atomic boundary.
- Do not let algorithms mutate shared dictionaries directly.
- Preserve `Decision` fields for CLI/API stability.
- Add tests before changing retry/reset timing semantics.
- Add tests before changing lock striping or eviction behavior.
- Keep unsafe demo implementations isolated under `teaching`.
- Keep CLI state-process-local note visible until a shared backend exists.
- Keep runtime dependencies empty unless a new ADR justifies adding one.
- Use `FakeClock` for deterministic tests instead of real sleeps wherever possible.

---

*Constitution reference: Article 6 (behavior verification), Article 5 (constraints and trade-offs), and Article 8 (verifiable learner work).*

---


# Lessons Learned
## App — Rate Limiter
**Rate Control Systems Group | Document 5 of 5**

---

## Why This Design Was Chosen

This design was chosen because rate limiting is not just one formula. It is a combination of algorithm behavior, time semantics, concurrency safety, storage lifecycle, metrics, and operator tooling.

The most important design choice is the storage mutation boundary. Without atomic read/modify/write, a limiter can over-admit under contention even if the algorithm looks correct on paper. Placing mutation behind `StorageBackend.mutate()` makes the safe path hard to misuse.

The second important choice is deterministic time. Token refill, window reset, sliding decay, TTL expiry, and scheduler decisions are all time-sensitive. `FakeClock` turns those behaviors into deterministic tests and clear demos.

The third important choice is CLI-first delivery. The CLI makes the system easy to demonstrate: users can run algorithm demos, hot-key contention, benchmarks, config-driven simulations, and failure demos without a web stack.

---

## What Was Intentionally Omitted

**Distributed storage:** Deferred because Redis/database semantics would dominate the capstone.

**Django middleware:** Deferred because the core build is CLI-first.

**Web dashboard:** Deferred because the README explicitly says there is no dashboard in the core build.

**Async-native limiter API:** Deferred because the current implementation is synchronous with thread-safe storage.

**Persistent CLI state:** Deferred because process-local in-memory state keeps the backend simple.

**Production benchmarks:** Deferred because local threaded benchmark numbers are exploratory.

**Full YAML dependency:** Optional only; core runtime stays dependency-free.

---

## Biggest Weakness

The biggest weakness is process-local state. A real production limiter usually needs shared state across workers, processes, machines, and restarts. This implementation is correct for a single process, but it is not a distributed rate-limiting service.

The second weakness is that CLI `inspect`, `reset`, and `list` build fresh in-memory limiters. That is honest for the backend, but it can surprise users expecting state to persist across commands.

The third weakness is that timing-dependent failure demos can vary across machines. They are valuable teaching tools, but they are not deterministic correctness tests.

---

## Scaling Considerations

**If the limiter becomes distributed:**
- introduce a Redis backend
- move atomic mutation into Redis Lua scripts or transactions
- define clock ownership carefully
- add network-failure behavior
- add consistency and retry policies

**If integrated into web frameworks:**
- add Django middleware
- add ASGI middleware
- define identity extraction policy
- define response header behavior
- define per-route/per-user rules

**If observability grows:**
- export Prometheus metrics
- add OpenTelemetry spans/events
- structure log fields consistently
- add dashboard integration

**If CLI state should persist:**
- add a file/database backend
- or add a daemon/service mode
- make `inspect` and `reset` target a shared backend

---

## What the Next Refactor Would Be

1. **Redis backend prototype** — preserve the current `StorageBackend` contract while adding distributed atomic operations.

2. **Middleware adapter layer** — add Django/ASGI wrappers after the core remains stable.

3. **Structured metric exporter** — expose metrics in Prometheus-friendly form.

4. **Config schema validation output** — improve config errors with line/context where possible.

5. **Exact sliding log algorithm** — add a fifth algorithm for comparison with sliding counter approximation.

---

## What This Project Taught

- **Correct algorithms can still race.** The unsafe demos show that correctness depends on atomic state transitions, not only formulas.

- **Time must be injectable.** Fake clocks make rate-limit tests reliable and understandable.

- **Storage is architecture.** TTL, LRU, snapshots, metrics pruning, and locks are not incidental; they define system behavior.

- **Different algorithms optimize different goals.** Token bucket supports bursts; fixed window is simple; sliding counter smooths boundaries; leaky bucket models draining queues.

- **Metrics shape product usefulness.** Operators need not only allowed/denied counts, but retry hints, reset hints, active keys, and memory estimates.

- **Scope discipline improves trust.** The project clearly says it is not a distributed production limiter and does not pretend otherwise.

---

*Constitution v2.0 checklist: This document satisfies Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity) for Rate Limiter.*
