# Algorithms

## Token Bucket

The token bucket stores `tokens` and `last_refill` per key. Each request refills
tokens from monotonic elapsed time, then consumes `cost` if enough capacity
exists. It absorbs bursts up to `capacity` and reports `retry_after` from the
missing token count divided by `refill_rate`.

Setting `refill_rate=0` creates a non-refilling bucket: capacity is fixed until
keys expire or are reset. This is useful for concurrency demos that must prove
admission never exceeds initial capacity.

## Fixed Window

The fixed window stores `window_start` and `count`. It is easy to reason about
but allows a boundary burst: requests near the end of one window and the start
of the next can double the apparent short-term rate.

## Sliding Window Counter

The sliding counter stores current and previous window counts. The effective
count is:

```text
current_count + previous_count * remaining_window_fraction
```

This smooths traffic compared with a fixed window and uses much less memory
than an exact timestamp log. It is approximate; a request can be denied because
weighted previous traffic still contributes to the estimate.

When monotonic time jumps forward by more than one window (for example after a
long idle period), the counter only remembers the current and previous windows.
Any traffic older than that is forgotten, which matches the approximation's
two-window memory budget.

## Leaky Bucket

The leaky bucket stores queue depth and last drain time. Accepted requests add
work to the queue; elapsed monotonic time drains the queue at a configured
rate. If `queue_depth + cost > capacity`, the limiter denies with a retry time
based on the overflow amount.

The autonomous drain worker calls the same public draining API used by tests
and demos. Request calls also drain from elapsed time, so the worker is useful
for visibility and queue-smoothing demonstrations rather than being required
for correctness.

## Oversized cost

A request whose `cost` exceeds the bucket's `capacity` (token, leaky) or the
window `limit` (fixed, sliding) can never succeed, because no amount of refill,
drain, or window roll-over makes room for it. In that case every algorithm
denies with `retry_after = None` and a reason of `cost exceeds capacity` /
`cost exceeds limit`, rather than returning a finite retry hint that would still
fail. A `cost` equal to capacity/limit is still satisfiable and keeps a normal
retry hint.

Non-finite costs (`NaN`, `Infinity`) are rejected with `InvalidCostError`.

## Decision reasons

Every allowed request returns `reason="allowed"` across all algorithms so CLI
output and metrics stay comparable.
