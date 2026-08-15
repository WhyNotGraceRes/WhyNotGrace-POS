"""Swiggy Partner API integration.

Same pattern as ZomatoProvider: no call is made, and no response is
fabricated, until SWIGGY_API_BASE_URL / SWIGGY_CLIENT_ID /
SWIGGY_CLIENT_SECRET are configured for a business.
"""
import hashlib
import hmac

import httpx

from app.core.config import get_settings
from app.services.integrations.base import IntegrationNotConfigured, MarketplaceProvider, MenuSyncResult

settings = get_settings()


class SwiggyProvider(MarketplaceProvider):
    provider_name = "SWIGGY"

    def _require_config(self, credentials: dict) -> None:
        if not settings.swiggy_api_base_url or not credentials.get("client_id") or not credentials.get("client_secret"):
            raise IntegrationNotConfigured(
                "Swiggy Partner API credentials are not configured. "
                "Set SWIGGY_API_BASE_URL and connect client_id/client_secret via "
                "PUT /integrations/swiggy/credentials once partner access is granted."
            )

    def sync_menu(self, *, credentials: dict, menu_payload: dict) -> MenuSyncResult:
        self._require_config(credentials)
        with httpx.Client(base_url=settings.swiggy_api_base_url, timeout=15) as client:
            response = client.post(
                "/menu/sync",
                json=menu_payload,
                headers={"Authorization": f"Bearer {credentials.get('access_token', '')}"},
            )
            response.raise_for_status()
            data = response.json()
        return MenuSyncResult(items_synced=len(menu_payload.get("items", [])), provider_menu_id=data.get("menu_id"))

    def push_order_status(self, *, credentials: dict, provider_order_id: str, status: str) -> None:
        self._require_config(credentials)
        with httpx.Client(base_url=settings.swiggy_api_base_url, timeout=15) as client:
            response = client.post(
                f"/orders/{provider_order_id}/status",
                json={"status": status},
                headers={"Authorization": f"Bearer {credentials.get('access_token', '')}"},
            )
            response.raise_for_status()

    def parse_inbound_order(self, *, payload: dict) -> dict:
        return {
            "provider_order_id": payload.get("order_id"),
            "items": payload.get("items", []),
            "customer_name": payload.get("customer", {}).get("name"),
            "customer_mobile": payload.get("customer", {}).get("phone"),
        }

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str, credentials: dict) -> bool:
        secret = settings.swiggy_webhook_secret
        if not secret:
            raise IntegrationNotConfigured("SWIGGY_WEBHOOK_SECRET is not configured.")
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


swiggy_provider = SwiggyProvider()
