# ADR 0003: CLI-First Interface

## Status
Accepted

## Context
The project is a student systems capstone that must expose a concrete user-facing
layer for demos, simulation, benchmarks, and operational inspection. A library-only
delivery would hide concurrency and lifecycle behavior behind test code. A web
dashboard would add frontend and deployment scope without strengthening the core
rate-limiting lessons.

## Decision
Treat the `ratelimit` CLI as the required user-facing interface. Core commands
include demo, simulate, benchmark, inspect, reset, list, and failure demos.
The Python library API remains public for tests and programmatic use, but capstone
acceptance and documentation center on CLI workflows.

No web dashboard ships in the core build; HTMX or similar UI integrations are
stretch goals.

## Consequences
- Users can explore algorithms, contention, and metrics without writing glue code.
- CLI process-local state is intentional: each command builds its own in-memory
  limiter (see ADR 0002).
- Stretch integrations (Django middleware, dashboards) attach to the library later
  rather than replacing the CLI-first core.
