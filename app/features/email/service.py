"""
Email service for sending emails using FastAPI-Mail.

This module provides a reusable EmailService class that handles sending emails
for various purposes such as password resets, email verification, notifications, etc.

All methods are async to ensure non-blocking operations.
"""

from html import escape
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType, NameEmail

from app.core.config import settings

TEMPLATES_DIR = Path(__file__).parent / "templates"


class EmailService:
    """
    Asynchronous service for sending emails without blocking the API.

    All methods are async to prevent blocking the main event loop when communicating
    with the mail server. This service is meant to be used with FastAPI's
    BackgroundTasks for non-blocking email operations.
    """

    def __init__(self):
        """Initialize EmailService with settings from environment."""
        self.config = ConnectionConfig(
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
            MAIL_STARTTLS=settings.MAIL_TLS,
            MAIL_SSL_TLS=settings.MAIL_SSL,
        )
        self.fm = FastMail(self.config)

    def _load_template(self, template_name: str) -> str:
        """
        Load an HTML template file.

        Args:
            template_name (str): Name of the template file (e.g., 'password_reset.html').

        Returns:
            str: Template content.

        Raises:
            FileNotFoundError: If template file doesn't exist.
        """
        template_path = TEMPLATES_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text()

    async def send_email(
        self,
        subject: str,
        recipients: list[NameEmail],
        body: str,
        subtype: MessageType = MessageType.html,
    ) -> bool:
        """
        Send an email to one or more recipients asynchronously.

        Args:
            subject (str): Email subject.
            recipients (list[NameEmail]): List of recipient email addresses.
            body (str): Email body content.
            subtype (MessageType): Email content subtype. Defaults to html.

        Returns:
            bool: True if email sent successfully, False otherwise.
        """
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=subtype,
        )
        try:
            await self.fm.send_message(message)
            return True
        except Exception:
            return False

    async def send_welcome_email(self, recipient_email: NameEmail, user_name: str) -> bool:
        """
        Send a welcome email to a new user asynchronously.

        Args:
            recipient_email (NameEmail): Recipient email address object.
            user_name (str): Name of the user.

        Returns:
            bool: True if email sent successfully, False otherwise.
        """
        try:
            subject = f"Welcome to {settings.MAIL_FROM_NAME}!"
            template = self._load_template("welcome.html")
            body = template.format(user_name=escape(user_name))

            return await self.send_email(
                subject=subject,
                recipients=[recipient_email],
                body=body,
            )
        except FileNotFoundError:
            return False
        except Exception:
            return False


email_service = EmailService()
