"""Email service abstraction.

Two backends:
- "console": logs the email instead of sending it. Development only —
  app.core.config.Settings.validate_production_safety() refuses to boot
  in production with this backend selected.
- "smtp": sends via SMTP using credentials from environment variables.

Callers (auth service) depend only on send_email(); the backend is an
implementation detail so a real provider (SES, Postmark, etc.) can be
swapped in later without touching call sites.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("whynotgrace.email")


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send_email(self, *, to: str, subject: str, body: str) -> None:
        if self.settings.email_backend == "console":
            logger.info("[DEV EMAIL] to=%s subject=%s\n%s", to, subject, body)
            return
        self._send_smtp(to=to, subject=subject, body=body)

    def _send_smtp(self, *, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.settings.smtp_from
        msg["To"] = to
        msg.set_content(body)

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as server:
            if self.settings.smtp_use_tls:
                server.starttls()
            if self.settings.smtp_username:
                server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.send_message(msg)


email_service = EmailService()
