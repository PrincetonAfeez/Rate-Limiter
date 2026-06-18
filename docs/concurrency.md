# Concurrency

The important race in a limiter is check-then-act:

```text
read state -> decide allowed -> write updated state
```

If two threads read the same state before either writes, both can admit a
request that only one should have admitted. A lock must cover the complete
read/modify/write operation.

This project uses `LockManager` to map keys to lock stripes. Requests for the
same stripe serialize, while independent stripes can proceed concurrently.
That is less contentious than a single global lock and simpler than creating
one lock object per key forever.

Thread stress tests are not formal proofs, so the tests assert deterministic
invariants such as "allowed count never exceeds capacity" rather than merely
checking that no exception occurred.

## Lock ordering and eviction

Holding more than one stripe at a time is dangerous. LRU eviction has to lock
the *victim's* stripe before deleting it, but if that happened while the
current request still held its own stripe, two writers could each wait on the
other's stripe and deadlock. The backend avoids this by committing the current
key's update, releasing its stripe, and only then evicting other keys — so a
mutation never holds two stripes at once. `tests/concurrency/`
`test_eviction_under_contention.py` reproduces the hazard with a two-stripe
lock manager and a tight LRU cap, and fails fast (via a watchdog) if the
ordering regresses.

