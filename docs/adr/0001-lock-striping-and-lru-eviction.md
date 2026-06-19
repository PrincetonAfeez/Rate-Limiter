# ADR 0001: Lock Striping and LRU Eviction Ordering

## Status
Accepted

## Context
The storage backend must safely mutate per-key rate-limiter state under concurrent access. A single global lock would be simple but overly restrictive. Per-key locks could grow without bound. Lock striping balances safety and memory use.

LRU eviction creates a lock-ordering hazard if the current key's stripe is held while acquiring a victim key's stripe.

## Decision
Use lock striping for key-level mutation. Complete the current key mutation under that key's stripe, release it, and only then evict LRU victims.

## Consequences
- Safe read/modify/write behavior for limiter state.
- Lower contention than a global lock.
- Avoids holding multiple stripe locks at once.
- LRU eviction may happen after the current mutation commits, which is acceptable for this in-memory backend.

## Deadlock and starvation risks

The backend avoids acquiring two stripe locks at once. LRU eviction is performed
only after the current mutation releases its stripe. This prevents circular wait
between concurrent mutations. Thread stress tests are not treated as proofs, so
tests assert deterministic invariants such as maximum allowed count and use
watchdogs for lock-ordering regressions.
