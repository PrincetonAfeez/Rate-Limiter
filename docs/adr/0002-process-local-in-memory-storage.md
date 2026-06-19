# ADR 0002: Process-Local In-Memory Storage

## Status
Accepted

## Context
The capstone must demonstrate atomic mutation, TTL expiry, LRU eviction, and safe
snapshots without shifting the core learning problem to distributed coordination.
A Redis or shared external store would introduce network failure modes, cross-process
locking, and deployment complexity before the in-process concurrency model is solid.

Each CLI invocation also needs a clear, self-contained backend: there is no shared
service layer in the core build.

## Decision
Use `InMemoryStorage` as the default and only core backend. State lives in
process-local memory with per-key TTL metadata, LRU eviction, and snapshot reads
that copy state without mutating limiter data. Each CLI command constructs its
own limiter instance; keys do not persist across separate command runs.

Redis and other shared backends remain stretch goals outside core scope.

## Consequences
- Focus stays on lock striping, mutation invariants, and storage lifecycle.
- Inspect, list, simulate, and metrics commands operate on a single process view.
- No cross-process or cross-host quota enforcement in the core build.
- Process-local memory must not be treated as a durable or security boundary for
  production systems.
