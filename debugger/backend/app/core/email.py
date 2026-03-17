import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_sync(to_email: str, subject: str, text: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())


async def send_verification_email(to_email: str, token: str, backend_url: str) -> None:
    link = f"{backend_url}/api/v1/auth/verify-email?token={token}"
    text = f"Verify your email by visiting: {link}\n\nThis link expires in {settings.VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes."
    html = (
        f"<p>Click the link below to verify your email address:</p>"
        f"<p><a href=\"{link}\">{link}</a></p>"
        f"<p>This link expires in {settings.VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.</p>"
    )
    if not settings.SMTP_HOST:
        if settings.DEV_SKIP_EMAIL:
            logger.warning("DEV_SKIP_EMAIL=true — skipping send. Verification link: %s", link)
            return
        raise RuntimeError("SMTP is not configured. Set SMTP_HOST or enable DEV_SKIP_EMAIL for local development.")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_sync, to_email, "Verify your email", text, html)
