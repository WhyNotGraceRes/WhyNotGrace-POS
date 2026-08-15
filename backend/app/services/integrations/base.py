"""Marketplace integration abstraction (Zomato, Swiggy, and any future
delivery marketplace). Concrete providers implement this interface.
No provider here fabricates a response — every method either performs a
real HTTP call using configured credentials, or raises
IntegrationNotConfigured so the caller can surface that clearly instead
of pretending the integration is live.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class IntegrationError(Exception):
    pass


class IntegrationNotConfigured(IntegrationError):
    """Raised when partner API credentials/access have not been
    provisioned yet. This is the expected state until Zomato/Swiggy grant
    partner API access — the architecture is complete, the connection is not.
    """


@dataclass
class MenuSyncResult:
    items_synced: int
    provider_menu_id: str | None


class MarketplaceProvider(ABC):
    provider_name: str

    @abstractmethod
    def sync_menu(self, *, credentials: dict, menu_payload: dict) -> MenuSyncResult: ...

    @abstractmethod
    def push_order_status(self, *, credentials: dict, provider_order_id: str, status: str) -> None: ...

    @abstractmethod
    def parse_inbound_order(self, *, payload: dict) -> dict:
        """Normalize a marketplace order payload into the shape expected
        by order_service.create_order (items, customer info, totals)."""
        ...

    @abstractmethod
    def verify_webhook_signature(self, *, raw_body: bytes, signature: str, credentials: dict) -> bool: ...
