# Project Scope (Summary)

This capstone delivers a CLI-first Python rate-limiting library demonstrating
concurrency, storage lifecycle, background workers, metrics, and deterministic
tests. See `rate_limiter_revised_scope.txt` for the full acceptance checklist.

## Core deliverables

- Four algorithms: token bucket, fixed window, sliding window counter, leaky bucket
- Shared `RateLimiter.try_acquire(key, cost=1) -> Decision` interface
- Lock striping with atomic `StorageBackend.mutate`
- In-memory backend with TTL, LRU eviction, and safe snapshots
- `SweeperWorker` and `LeakyBucketDrainWorker` with clean lifecycle
- Metrics, structured logging, and CLI demos/simulation/benchmark commands
- Deliberately unsafe teaching implementations under `ratelimiter.teaching`

## Architecture boundaries

| Layer | Responsibility |
|-------|----------------|
| `core` | Protocols, `Decision`, config, clock, errors |
| `factory` | Public limiter construction from rules/flags |
| `algorithms` | Rate-limit logic via storage mutation |
| `storage` | Persistence, TTL, LRU, snapshots |
| `concurrency` | Lock striping |
| `workers` | Scheduler, sweeper, drain worker |
| `observability` | Metrics and structured logs |
| `cli` | User-facing commands |
| `teaching` | Unsafe race demos (not default API) |

## Stretch (out of core scope)

Redis backend, asyncio variant, sliding window log, Django middleware, HTMX dashboard.

## Invariants tested

- Never over-admit under safe implementations
- Non-negative `retry_after` / `reset_after`
- Monotonic time for all limit calculations
- Workers stop cleanly after `stop()` + `join()`
- Metrics reads do not mutate limiter state

## CLI process-local state

Each CLI command builds its own in-memory limiter. `ratelimit list` shows configured
rules only; it does not aggregate keys from other commands or prior runs. To see
which keys were touched in a workload, use `ratelimit simulate` and read its
`active_keys` field.
