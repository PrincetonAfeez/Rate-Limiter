"""Test fixtures for traffic patterns."""

def hot_key(index: int) -> str:
    return "hot"


def many_keys(index: int, count: int = 10) -> str:
    return f"key-{index % count}"

