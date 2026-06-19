# Schema Folder

Simple JSON Schema files for the `capstone-rate-limiter` project.

## Files

- `config.schema.json` — validates limiter config files that use a top-level `limiters` or `rules` mapping.
- `decision.schema.json` — validates `Decision.to_dict()` output from limiter calls.
- `metrics.schema.json` — validates `MetricsCollector.snapshot()` output.
- `cli-simulate-output.schema.json` — validates JSON output from `ratelimit simulate`.
- `cli-benchmark-output.schema.json` — validates JSON output from `ratelimit benchmark`.
- `cli-list-output.schema.json` — validates JSON output from `ratelimit list`.
- `cli-inspect-output.schema.json` — validates JSON output from `ratelimit inspect`.
- `cli-reset-output.schema.json` — validates JSON output from `ratelimit reset`.

## Example validation

```bash
python -m pip install jsonschema
jsonschema -i configs/sample_limits.json Schema/config.schema.json
```

The schemas use JSON Schema Draft 2020-12.
