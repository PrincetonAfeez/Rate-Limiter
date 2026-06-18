# Storage

Algorithms depend on `StorageBackend`, not raw dictionaries. The backend owns:

- Atomic mutation hooks.
- State creation and lookup.
- Reset and listing.
- TTL metadata.
- LRU eviction.
- Safe snapshots.
- Approximate memory estimates.

The in-memory backend stores dataclass state objects. Snapshot reads copy those
objects into serializable mappings so inspect, list, and metrics commands do
not mutate limiter state.

Sample configs live in `configs/` as TOML, YAML, and JSON.

The Redis backend is intentionally left as a stretch feature because it changes
the main learning problem from in-process synchronization to distributed atomic
operations.

