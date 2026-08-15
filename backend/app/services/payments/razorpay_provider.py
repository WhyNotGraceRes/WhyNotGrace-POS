import hashlib
import hmac

import razorpay
from razorpay.errors import SignatureVerificationError

from app.services.payments.base import PaymentProvider, PaymentProviderNotConfigured, ProviderOrder


class RazorpayProvider(PaymentProvider):
    """Stateless: every call resolves its own razorpay.Client from the
    credentials the caller passes in (per-business, resolved by
    payment_service). Never caches a client keyed only by provider, since
    that would leak one business's credentials into another's requests.
    """

    def _client(self, credentials: dict[str, str | None]) -> razorpay.Client:
        key_id = credentials.get("key_id")
        key_secret = credentials.get("key_secret")
        if not key_id or not key_secret:
            raise PaymentProviderNotConfigured(
                "Razorpay is not configured for this business. Connect Razorpay credentials first."
            )
        return razorpay.Client(auth=(key_id, key_secret))

    def create_order(
        self, *, credentials: dict[str, str | None], amount_paise: int, currency: str, receipt: str
    ) -> ProviderOrder:
        client = self._client(credentials)
        order = client.order.create(
            {"amount": amount_paise, "currency": currency, "receipt": receipt, "payment_capture": 1}
        )
        return ProviderOrder(provider_order_id=order["id"], amount_paise=amount_paise, currency=currency)

    def verify_payment_signature(
        self, *, credentials: dict[str, str | None], provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool:
        client = self._client(credentials)
        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": provider_order_id,
                    "razorpay_payment_id": provider_payment_id,
                    "razorpay_signature": signature,
                }
            )
            return True
        except SignatureVerificationError:
            return False

    def verify_webhook_signature(self, *, credentials: dict[str, str | None], raw_body: bytes, signature: str) -> bool:
        webhook_secret = credentials.get("webhook_secret")
        if not webhook_secret:
            raise PaymentProviderNotConfigured("Razorpay webhook secret is not configured for this business.")
        expected = hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


razorpay_provider = RazorpayProvider()
