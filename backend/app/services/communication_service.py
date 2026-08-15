"""Abstraction point for future SMS / WhatsApp / push notification
delivery (birthday offers, loyalty rewards, order status updates).

Only email is actually wired up today. This class exists so
loyalty/marketing code can call a single interface now, and additional
channels can be added later without changing call sites. Every send
respects the customer's opt-in flags — callers MUST check
Customer.marketing_opt_in / sms_opt_in / whatsapp_opt_in before calling.
"""
import logging

from app.models.enums import CommunicationChannel

logger = logging.getLogger("whynotgrace.communication")


class CommunicationService:
    def send(self, *, channel: CommunicationChannel, to: str, message: str) -> None:
        if channel == CommunicationChannel.EMAIL:
            from app.services.email_service import email_service

            email_service.send_email(to=to, subject="WhyNotGrace", body=message)
            return

        # SMS / WhatsApp / Push: no provider configured yet. Log instead of
        # silently pretending delivery succeeded.
        logger.info("[UNCONFIGURED CHANNEL %s] to=%s message=%s", channel.value, to, message)


communication_service = CommunicationService()
