"""Abstract base class for alert payload adapters."""

from abc import ABC, abstractmethod
from typing import Any

from src.schemas.universal_alert import UniversalAlertPayload


class BaseAlertAdapter(ABC):
    """Interface for adapting external monitoring payloads to UniversalAlertPayload."""

    @abstractmethod
    def adapt(self, raw_payload: dict[str, Any]) -> UniversalAlertPayload:
        """Parse raw vendor payload into a standardized UniversalAlertPayload."""
        raise NotImplementedError
