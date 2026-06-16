# Rate Limiter Capstone

A reusable Python rate-limiting library and CLI that demonstrates algorithms,
atomic state mutation, lock striping, storage lifecycle, background workers,
metrics, deterministic tests, and deliberate race-condition demos.

The command-line interface is the required user-facing layer. There is no web
dashboard in the core build.

## Quickstart

```powershell
python -m pip install -e .
ratelimit demo all
ratelimit simulate --algorithm token --keys 100 --requests 10000 --threads 8
ratelimit benchmark --algorithms token,fixed-window,sliding-window-counter,leaky --keys 1000 --threads 16
pytest
mypy src
```

Without installing, the same commands can be run as:

```powershell
$env:PYTHONPATH = "src"
python -m ratelimiter.cli.main demo all
```

## Public API

Every algorithm implements:

```python
try_acquire(key: str, cost: int | float = 1) -> Decision
```

`Decision` includes `allowed`, `remaining`, `retry_after`, `reset_after`,
`limit`, `algorithm`, and `reason`. Denied decisions explain why the request
was rejected and never return negative timing values.

## Algorithms

- Token bucket: burst capacity plus steady refill.
- Fixed window: simple per-window counter that intentionally shows boundary
  bursts.
- Sliding window counter: weighted approximation of current and previous
  windows.
- Leaky bucket: queue-depth model that drains at a steady rate and supports an
  autonomous drain worker.

See [docs/algorithms.md](docs/algorithms.md) for tradeoffs.

## Concurrency

Algorithms never mutate raw dictionaries directly. They call
`StorageBackend.mutate`, which creates or reads state and runs the full
read/modify/write operation under the key's lock stripe. This is the key
invariant: the check and the update are one atomic operation from the
algorithm's point of view.

The `teaching` package contains unsafe implementations that intentionally read
outside a lock and update later. They are used only by tests and demos:

```powershell
ratelimit failure-demo race
ratelimit demo concurrency-unsafe
```

See [docs/concurrency.md](docs/concurrency.md) and
[docs/failure_demos.md](docs/failure_demos.md).

## Storage And Lifecycle

The default `InMemoryStorage` backend supports:

- Per-key lock striping.
- TTL metadata and expiry.
- LRU eviction cap.
- Safe snapshots for CLI and metrics.
- Approximate memory estimates for demos and benchmarks.

`SweeperWorker` expires idle keys without requiring new request traffic.

## Workers

Workers expose `start()`, `stop()`, `join(timeout=None)`, `is_running()`, and
context-manager usage. Tests assert that worker threads stop cleanly.

## Configuration

Limiters can be described declaratively in TOML, JSON, or YAML and used to drive
a running limiter, not just listed:

```toml
[limiters.api]
rule = "10/sec burst 20 algorithm token"
```

```powershell
ratelimit simulate --config configs/sample_limits.toml --name api --requests 1000
ratelimit inspect user-123 --config configs/sample_limits.toml --name login
```

### Rule grammar

A rule string has the form:

```text
<limit>/<unit> [burst <n>] [algorithm <name>]
```

- **limit** — a positive number (e.g. `100`, `2.5`).
- **unit** — one of `s`/`sec`/`second`/`seconds`, `m`/`min`/`minute`/`minutes`,
  `h`/`hr`/`hour`/`hours`.
- **burst** *(optional)* — token-bucket / leaky-bucket capacity; defaults to
  `limit` when omitted.
- **algorithm** *(optional, default `token`)* — one of `token` (`token-bucket`),
  `fixed`/`fixed-window`, `sliding`/`sliding-counter`/`sliding-window-counter`,
  or `leaky`/`leaky-bucket`.

Examples: `100/min`, `10/sec burst 20`, `100/hour algorithm fixed-window`,
`50/min algorithm sliding-window-counter`.

Rule strings parse into a `LimitRule` (limit, period, optional `burst`, and
`algorithm`); YAML uses PyYAML when installed and a minimal built-in parser
otherwise, so the core library has no required runtime dependencies.

## Observability

The library records per-key allowed/denied counts, denial rate, current usage
(tokens spent, window count, or queue depth), last decision time, and denial
reason. Per-key metrics are pruned when a key is expired, evicted, or reset, so
`total_keys` tracks currently active keys. Global metrics include allowed/denied
totals, active keys, expired and evicted key counts, worker lifecycle events,
worker errors, and memory estimates.

Structured logs are emitted as JSON strings through Python's standard logging
module.

## What Is Intentionally Not Production-Ready

This is a serious student systems capstone, not a distributed production
rate-limiting service. The in-memory backend is process-local. Benchmarks are
for comparison and exploration, not correctness proof. Redis, asyncio, Django
middleware, and a dashboard are stretch integrations after the core system is
complete.
