"""Asynchronous Redis client for alert deduplication and storm protection."""

import logging
from typing import TYPE_CHECKING, Any, Self

import fakeredis
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

if TYPE_CHECKING:
    from redis.asyncio import ConnectionPool, Redis

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Asynchronous Redis client managing an async connection pool.
    Caches alert signatures to prevent alert storms and duplicate ticketing.
    Includes in-memory fallback if standalone Redis is temporarily unreachable.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        pool: "ConnectionPool[Any] | None" = None,
        client: "Redis[Any] | None" = None,
    ) -> None:
        """
        Initialize the Redis client with an async connection pool.

        Args:
            redis_url: Redis connection URL (e.g. "redis://localhost:6379")
            pool: Optional pre-configured ConnectionPool instance
            client: Optional pre-configured Redis client (useful for mocks/tests)
        """
        self.redis_url = redis_url
        self._external_client = client is not None
        self._fallback_client: Any = None
        # Internal client and pool stored as Any to accommodate both redis.asyncio.Redis
        # (decode_responses=True → Redis[str]) and fakeredis.FakeAsyncRedis test doubles.
        self._client: Any
        self._pool: Any

        if client is not None:
            self._client = client
            self._pool = None
        elif pool is not None:
            self._pool = pool
            self._client = aioredis.Redis(connection_pool=pool, decode_responses=True)
        else:
            self._pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            self._client = aioredis.Redis(
                connection_pool=self._pool, decode_responses=True
            )

    def _get_active_client(self) -> Any:
        """Return fallback client if active, otherwise primary client."""
        if self._fallback_client is not None:
            return self._fallback_client
        return self._client

    def _format_key(self, signature: str) -> str:
        """Standardize cache key prefix for alert deduplication."""
        return f"alert:dedup:{signature}"

    async def check_and_set_dedup(
        self,
        signature: str,
        ttl_seconds: int = 900,
    ) -> str | None:
        """
        Check if the alert signature exists in Redis.

        If the signature exists, return the stored Jira ticket key.
        If it does not exist, return None (key is only set after successful Jira creation).

        Args:
            signature: SHA-256 hash representing the alert signature
            ttl_seconds: TTL duration (default: 900s / 15 minutes)

        Returns:
            Existing Jira ticket key if cached, else None
        """
        cache_key = self._format_key(signature)
        try:
            client = self._get_active_client()
            cached_ticket: str | None = await client.get(cache_key)
            if cached_ticket:
                logger.info(
                    "Deduplication cache HIT for signature %s -> existing ticket: %s",
                    signature,
                    cached_ticket,
                )
                return cached_ticket

            logger.debug("Deduplication cache MISS for signature %s", signature)
            return None
        except (
            ConnectionRefusedError,
            RedisConnectionError,
            RedisTimeoutError,
            OSError,
        ) as conn_err:
            if not self._external_client and self._fallback_client is None:
                logger.warning(
                    "Primary Redis at %s unreachable (%s). Initializing in-memory deduplication cache fallback.",
                    self.redis_url,
                    conn_err,
                )
                self._fallback_client = fakeredis.FakeAsyncRedis(decode_responses=True)
                result: str | None = await self._fallback_client.get(cache_key)
                return result

            logger.warning(
                "Redis connection error during deduplication check for %s: %s",
                signature,
                conn_err,
            )
            return None
        except RedisError as exc:
            logger.warning(
                "Redis read error during deduplication check for %s: %s",
                signature,
                exc,
            )
            return None

    async def set_dedup(
        self,
        signature: str,
        ticket_key: str,
        ttl_seconds: int = 900,
    ) -> None:
        """
        Store the Jira ticket key for the given alert signature with a TTL.

        Args:
            signature: SHA-256 hash representing the alert signature
            ticket_key: Jira issue key (e.g. "KAN-5") to associate
            ttl_seconds: TTL in seconds (default: 900s / 15 minutes)
        """
        cache_key = self._format_key(signature)
        try:
            client = self._get_active_client()
            await client.set(cache_key, ticket_key, ex=ttl_seconds)
            logger.info(
                "Deduplication cache saved: %s -> %s (TTL: %ds)",
                cache_key,
                ticket_key,
                ttl_seconds,
            )
        except (
            ConnectionRefusedError,
            RedisConnectionError,
            RedisTimeoutError,
            OSError,
        ) as conn_err:
            if not self._external_client and self._fallback_client is None:
                logger.warning(
                    "Primary Redis at %s unreachable (%s). Saving to in-memory deduplication cache fallback.",
                    self.redis_url,
                    conn_err,
                )
                self._fallback_client = fakeredis.FakeAsyncRedis(decode_responses=True)
                await self._fallback_client.set(cache_key, ticket_key, ex=ttl_seconds)
                return

            logger.warning(
                "Redis connection error when saving deduplication key %s: %s",
                signature,
                conn_err,
            )
        except RedisError as exc:
            logger.warning(
                "Redis write error when saving deduplication key %s: %s",
                signature,
                exc,
            )

    async def aclose(self) -> None:
        """Gracefully close the Redis client and connection pool."""
        if not self._external_client:
            try:
                await self._client.aclose()
            except AttributeError:
                await self._client.close()
            if self._pool is not None:
                try:
                    await self._pool.aclose()
                except (AttributeError, TypeError):
                    self._pool.disconnect()
        if self._fallback_client is not None:
            await self._fallback_client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
