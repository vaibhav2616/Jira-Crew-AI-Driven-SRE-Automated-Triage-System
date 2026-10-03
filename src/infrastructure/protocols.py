"""Structural protocols for SRE triage infrastructure clients.

Using runtime_checkable Protocol interfaces allows TriageService to accept
both real production clients and lightweight test doubles without requiring
inheritance, eliminating mypy incompatible-type errors on mock injection.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Structural protocol for LLM analysis clients."""

    async def analyze_alert(
        self,
        service_name: str,
        error_message: str,
        raw_logs: dict[str, Any],
    ) -> Any:
        """Analyze an alert and return a structured triage result."""
        ...


@runtime_checkable
class RedisClientProtocol(Protocol):
    """Structural protocol for Redis deduplication cache clients."""

    async def check_and_set_dedup(
        self,
        signature: str,
        ttl_seconds: int = 900,
    ) -> str | None:
        """Check if signature exists; return ticket key or None."""
        ...

    async def set_dedup(
        self,
        signature: str,
        ticket_key: str,
        ttl_seconds: int = 900,
    ) -> None:
        """Store ticket key for signature with TTL."""
        ...
