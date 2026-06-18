# CLI

Required commands are implemented with `argparse`:

```powershell
ratelimit demo all
ratelimit demo fixed-window-boundary
ratelimit demo token-bucket-burst
ratelimit demo sliding-window-counter
ratelimit demo leaky-bucket-drain
ratelimit demo ttl-sweeper
ratelimit demo concurrency-safe
ratelimit demo concurrency-unsafe
ratelimit simulate --algorithm token --keys 100 --requests 10000 --threads 8
ratelimit simulate --algorithm token --hot-key --requests 5000 --threads 16
ratelimit simulate --algorithm token --cost 2 --limit 10 --requests 100
ratelimit inspect user-123
ratelimit reset user-123
ratelimit list
ratelimit benchmark --algorithms token,fixed-window,sliding-window-counter,leaky --keys 1000 --threads 16
ratelimit benchmark --algorithms token --keys 100 --requests 1000 --cost 2
ratelimit failure-demo race
```

`simulate` and `inspect` can build the limiter from a declarative config file
instead of flags, so a config rule actually drives a running limiter:

```powershell
ratelimit simulate --config configs/sample_limits.toml --name api --requests 1000
ratelimit simulate --config configs/sample_limits.json --name login --requests 100
ratelimit inspect user-123 --config configs/sample_limits.toml --name login
ratelimit reset user-123 --config configs/sample_limits.toml --name login
ratelimit list --config configs/sample_limits.yaml
```

CLI output comes from `Decision` objects, metrics snapshots, and storage
snapshots. `inspect` is read-only: it reads a state snapshot and never calls
`try_acquire`, so inspecting a key cannot consume its capacity. Inspect also
surfaces `last_retry_after` and `last_reset_after` from per-key metrics.

The CLI is intentionally process-local: each command builds its own in-memory
limiter. `list` reports configured rules (from `--config` or built-in demos) and
always returns an empty `active_keys` list — keys from other commands or prior
runs are not visible. To see which keys a workload touched, run
`ratelimit simulate ...` and read its `active_keys` field, or use the library
API and call `storage.list_keys()` on the same limiter instance. A shared
backend (e.g. Redis) would change this behavior.

`ratelimit benchmark` prints JSON to stdout and emits a structured
`benchmark.summary` log event with per-algorithm throughput, allow/deny counts,
memory estimates, and the `--cost` value used per request.

`ratelimit --version` prints the package version.

## Testing

Most tests use `FakeClock` for deterministic behavior. A few concurrency race
demos are marked `@pytest.mark.timing_dependent` because they rely on thread
scheduling. CI skips those by default; run the full suite locally with plain
`pytest`, or skip timing-sensitive tests with:

```powershell
pytest -m "not timing_dependent"
```

## Exit codes

Usage errors and runtime errors are deliberately distinct:

- `0` — success.
- `1` — runtime error (e.g. an unknown algorithm, or an unknown limiter name in
  `--config`). A clean one-line message is printed to stderr with no usage dump.
- `2` — usage error from argument parsing (unknown command/flag, or a value that
  fails validation such as `--period-seconds 0`). argparse prints usage.

