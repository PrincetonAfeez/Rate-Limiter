# Tradeoffs

This project favors clear contracts and deterministic tests over production
feature breadth.

- In-memory storage is easy to inspect but cannot coordinate across processes.
- Lock striping reduces contention but unrelated keys can still collide on the
  same stripe.
- Sliding window counters are smoother than fixed windows but approximate.
- Background workers improve lifecycle and scheduling practice but are not a
  replacement for atomic request-time mutation.
- Benchmarks are useful for comparison, never for proving correctness.

