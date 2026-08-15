"""Payment provider abstraction. Concrete providers (Razorpay today, others
later) implement this interface so app/services/payment_service.py never
depends on a specific vendor SDK directly.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderOrder:
    provider_order_id: str
    amount_paise: int
    currency: str


class PaymentProviderError(Exception):
    pass


class PaymentProviderNotConfigured(PaymentProviderError):
    """Raised when credentials for a provider are missing. Callers must
    surface this clearly rather than silently pretending payment succeeded.
    """


class PaymentProvider(ABC):
    """credentials is always resolved by the caller for the current business
    (see payment_service._resolve_razorpay_credentials) — a provider
    instance never caches or defaults to global credentials itself, so a
    request for Business A can never accidentally use Business B's (or a
    stale) client/secret.
    """

    @abstractmethod
    def create_order(
        self, *, credentials: dict[str, str | None], amount_paise: int, currency: str, receipt: str
    ) -> ProviderOrder: ...

    @abstractmethod
    def verify_payment_signature(
        self, *, credentials: dict[str, str | None], provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool: ...

    @abstractmethod
    def verify_webhook_signature(self, *, credentials: dict[str, str | None], raw_body: bytes, signature: str) -> bool: ...
