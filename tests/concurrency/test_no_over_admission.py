"""Test no over admission."""

from concurrent.futures import ThreadPoolExecutor

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter


def test_safe_token_bucket_never_over_admits_hot_key() -> None:
    limiter = TokenBucketLimiter(capacity=20, refill_rate=0)

    with ThreadPoolExecutor(max_workers=32) as executor:
        decisions = list(executor.map(lambda _: limiter.try_acquire("hot"), range(200)))

    assert sum(decision.allowed for decision in decisions) == 20

