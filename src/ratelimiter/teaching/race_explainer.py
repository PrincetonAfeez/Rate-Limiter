"""ASCII timelines explaining check-then-act races for teaching demos."""

from __future__ import annotations


def check_then_act_timeline() -> list[str]:
    """Return a short timeline of the classic limiter race."""

    return [
        "check-then-act race timeline (two threads, limit=1):",
        "",
        "  Thread A                    Thread B",
        "  ---------                   ---------",
        "  read count=0",
        "                              read count=0",
        "  decide: allowed",
        "                              decide: allowed",
        "  sleep (race window)",
        "                              sleep (race window)",
        "  write count=1",
        "                              write count=1",
        "",
        "  Both threads believed capacity existed. Result: 2 admissions for limit 1.",
        "",
        "Safe fix: read + decide + write inside one lock stripe via StorageBackend.mutate.",
    ]


def over_admission_summary(*, expected: int, actual: int) -> str:
    """Summarize over-admission for CLI output."""

    over = max(0, actual - expected)
    return f"expected max={expected}, actual allowed={actual}, over-admission={over}"
