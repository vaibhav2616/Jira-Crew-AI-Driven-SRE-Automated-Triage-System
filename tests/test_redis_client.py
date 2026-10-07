"""Unit tests for asynchronous RedisClient."""

import fakeredis
import pytest

from src.infrastructure.redis_client import RedisClient


@pytest.mark.asyncio
async def test_redis_client_check_and_set_dedup_flow() -> None:
    """Verify check_and_set_dedup miss, set_dedup, and subsequent hit."""
    fake_async_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    redis_client = RedisClient(client=fake_async_redis)

    test_sig = "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"

    # 1. Cache MISS on initial check: returns None and does not set key
    res_initial = await redis_client.check_and_set_dedup(test_sig, ttl_seconds=900)
    assert res_initial is None

    # Key must NOT exist in Redis yet
    assert await fake_async_redis.get(f"alert:dedup:{test_sig}") is None

    # 2. Store ticket key after ticket creation
    await redis_client.set_dedup(test_sig, "KAN-101", ttl_seconds=900)

    # Key must now exist in Redis with value
    assert await fake_async_redis.get(f"alert:dedup:{test_sig}") == "KAN-101"

    # 3. Cache HIT on recurring alert check: returns stored ticket key
    res_recurring = await redis_client.check_and_set_dedup(test_sig, ttl_seconds=900)
    assert res_recurring == "KAN-101"

    await redis_client.aclose()


@pytest.mark.asyncio
async def test_redis_client_handles_read_exception_gracefully() -> None:
    """Verify check_and_set_dedup fails open (returns None) on Redis errors."""

    class BrokenRedis:
        async def get(self, key: str) -> str | None:
            raise ConnectionError("Redis cluster unreachable")

    broken_client = RedisClient(client=BrokenRedis())  # type: ignore[arg-type]
    res = await broken_client.check_and_set_dedup("some-sig")
    assert res is None
