# Rate Limiter Capstone

A reusable Python rate-limiting library and CLI that demonstrates algorithms,
atomic state mutation, lock striping, storage lifecycle, background workers,
metrics, deterministic tests, and deliberate race-condition demos.

The command-line interface is the required user-facing layer. There is no web
dashboard in the core build.

## Quickstart

```powershell
python -m pip install -r requirements-dev.lock.txt
# or: pip install -e ".[all]"
# or: pip install -r requirements-dev.txt
ratelimit demo all
ratelimit simulate --algorithm token --keys 100 --requests 10000 --threads 8
ratelimit simulate --algorithm token --cost 2 --limit 10 --requests 100
ratelimit simulate --algorithm token --hot-key --requests 5000 --threads 16
ratelimit benchmark --algorithms token,fixed,sliding,leaky --keys 1000 --threads 16 --cost 1
pytest --cov=ratelimiter
mypy src
```

Install options:

| Command | What you get |
|---------|----------------|
| `pip install -e .` | Library + `ratelimit` CLI only (zero runtime deps) |
| `pip install -e ".[dev]"` | + pytest, mypy, pytest-cov |
| `pip install -e ".[yaml]"` | + PyYAML for full YAML config parsing |
| `pip install -e ".[all]"` | Dev tools and PyYAML together |
| `pip install -r requirements-dev.txt` | Same as `.[all]` via requirements files |
| `pip install -r requirements-dev.lock.txt` | Same as `.[all]`, with pinned transitive versions |

Regenerate the lockfile after changing dev dependencies in `pyproject.toml`:

```powershell
pip install pip-tools
pip-compile requirements-dev.in -o requirements-dev.lock.txt
```

Without installing, the same commands can be run as:

```powershell
$env:PYTHONPATH = "src"
python -m ratelimiter.cli.main demo all
```

The installable package name is `capstone-rate-limiter` (see `pyproject.toml`);
import it in Python as `ratelimiter`.

## Public API

Every algorithm implements:

```python
try_acquire(key: str, cost: int | float = 1) -> Decision
```

Key library exports also include `LimitRule`, `load_config`, `ConfigError`,
`build_limiter`, `build_limiter_from_rule`, `require_inspectable`, `rule_from_config`,
`MetricsCollector`, `SweeperWorker`, `LeakyBucketDrainWorker`, and the
`InspectableLimiter` protocol for CLI-style inspection.

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

## Deterministic Time (`FakeClock`)

All time-based logic uses monotonic time via the injectable `Clock` protocol.
Tests and demos inject `FakeClock` so refill, window roll-over, TTL expiry, and
scheduler behavior are deterministic without real sleeps:

```python
from ratelimiter import FakeClock, TokenBucketLimiter

clock = FakeClock()
limiter = TokenBucketLimiter(capacity=3, refill_rate=1, clock=clock)
limiter.try_acquire("user")
clock.advance(1.0)
limiter.try_acquire("user")  # tokens refilled predictably
```

Background worker thread loops still wait on the host clock; tests drive
`MonotonicScheduler.run_pending()` directly when they need fake-time scheduling.
See [docs/workers.md](docs/workers.md).

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

## Testing

The suite has **220+ tests** with **~99% line coverage** on `ratelimiter` (95%
minimum enforced in CI via `pyproject.toml`). Most tests use `FakeClock` for
deterministic time-based behavior.

A small number of concurrency race demos are marked
`@pytest.mark.timing_dependent` because they rely on thread scheduling and
intentional delays in the unsafe teaching implementations:

```powershell
pytest                              # full local suite (222 tests)
pytest --cov=ratelimiter            # with coverage report (95% gate)
pytest -m "not timing_dependent"    # CI-safe subset (220 tests)
pytest -m timing_dependent          # race demos only (2 tests)
mypy src                            # strict type check
```

GitHub Actions runs the CI-safe subset plus mypy on Python 3.11 and 3.12, and
runs timing-dependent tests in a separate job on Python 3.12.

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
ratelimit simulate --config configs/sample_limits.json --name login --requests 100
ratelimit inspect user-123 --config configs/sample_limits.toml --name login
ratelimit reset user-123 --config configs/sample_limits.toml --name login
ratelimit list --config configs/sample_limits.yaml
```

Sample configs are provided in TOML, YAML, and JSON under `configs/`.

### Process-local CLI state

Each CLI command builds its own in-memory limiter instance. Keys created by
`simulate` do not persist into a later `inspect`, `reset`, or `list` invocation.
`ratelimit list` therefore reports configured rules but returns an empty
`active_keys` list unless you use the library API or run traffic and inspection
in the same Python process. `ratelimit simulate` includes an `active_keys` field
for keys touched during that run. This is intentional for the capstone backend; a
shared store (e.g. Redis) is a stretch goal.

### Rule grammar

A rule string has the form:

```text
<limit>/<unit> [burst <n>] [algorithm <name>]
```

- **limit** — a positive number (e.g. `100`, `2.5`).
- **unit** — one of `s`/`sec`/`second`/`seconds`, `m`/`min`/`minute`/`minutes`,
  `h`/`hr`/`hour`/`hours`.
- **burst** *(optional)* — token-bucket / leaky-bucket capacity only; using
  `burst` with fixed-window or sliding-window rules is a config error. Defaults
  to `limit` when omitted for supported algorithms.
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
(tokens spent, window count, or queue depth), last decision time, denial
reason, and the most recent `retry_after` / `reset_after` hints. Per-key metrics
are pruned when a key is expired, evicted, or reset, so `total_keys` tracks
currently active keys. Global metrics include allowed/denied totals, active keys,
expired and evicted key counts, worker lifecycle events, worker errors, and
memory estimates.

Denied decisions are logged at WARNING level; allowed decisions at INFO.
Benchmark runs emit a structured `benchmark.summary` log event with per-algorithm
throughput, allow/deny counts, memory estimates, and the `--cost` value used.

Structured logs are emitted as JSON strings through Python's standard logging
module.

## What Is Intentionally Not Production-Ready

This is a serious student systems capstone, not a distributed production
rate-limiting service. The in-memory backend is process-local. Benchmarks are
for comparison and exploration, not correctness proof. Redis, asyncio, Django
middleware, and a dashboard are stretch integrations after the core system is
complete.

## Security posture

This project is a CLI-first educational rate-limiting library. It protects only
the in-process limiter state from unsafe concurrent mutation. It does not
provide authentication, authorization, encryption, network isolation, distributed
quota enforcement, Redis-backed coordination, API gateway protection, abuse
detection, or tenant isolation.

The default storage backend is process-local memory. It should not be treated as
a security boundary for production systems. Unsafe implementations under
`ratelimiter.teaching` are intentionally vulnerable race-condition demos and are
not part of the normal public API.
