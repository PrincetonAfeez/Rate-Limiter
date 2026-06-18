# Failure Demos

Unsafe implementations live under `ratelimiter.teaching`. They are clearly
labeled and are not exported from the normal package API. The same classes are
also re-exported from `ratelimiter.concurrency.unsafe` for compatibility with
the project scope document.

## Fixed window race

The unsafe fixed-window demo reads a counter, sleeps briefly, then writes the
updated value. Under high contention many threads read the same old counter and
all decide they can proceed. The reported allowed count can exceed the expected
limit.

## Token bucket race

The unsafe token-bucket demo uses the same check-then-act pattern without lock
striping. With `refill_rate=0`, the expected maximum equals capacity; unsafe
threads can still over-admit when they read the same token count before writing.

See `ratelimiter.teaching.race_explainer` for an ASCII timeline of the race.

Unsafe implementations use distinct `reason` strings (for example
`allowed by unsafe check-then-act path`) so demos can tell them apart from the
production `"allowed"` / denial reasons.

Run:

```powershell
ratelimit failure-demo race
ratelimit demo concurrency-unsafe
```

The safe implementation uses `StorageBackend.mutate`, which keeps the read,
decision, and update inside one atomic backend mutation.
