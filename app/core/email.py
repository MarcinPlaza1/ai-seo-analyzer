from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.config.settings import settings

class EmailService:
    def __init__(self):
        self.config = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            SUPPRESS_SEND=settings.SUPPRESS_SEND,
            TIMEOUT=settings.TIMEOUT,
            VALIDATE_CERTS=settings.VALIDATE_CERTS
        )
        self.fastmail = FastMail(self.config)

    async def send_email(
        self,
        email_to: List[str],
        subject: str,
        body: str
    ) -> None:
        message = MessageSchema(
            subject=subject,
            recipients=email_to,
            body=body,
            subtype="html"
        )
        
        await self.fastmail.send_message(message)

    async def send_activation_email(self, email_to: str, token: str) -> None:
        activation_link = f"{settings.FRONTEND_URL}/activate?token={token}"
        await self.send_email(
            [email_to],
            "Aktywuj swoje konto",
            f"Kliknij w link, aby aktywować konto: <a href='{activation_link}'>{activation_link}</a>"
        )

    async def send_password_reset_email(self, email_to: str, token: str) -> None:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await self.send_email(
            [email_to],
            "Reset hasła",
            f"Kliknij w link, aby zresetować hasło: <a href='{reset_link}'>{reset_link}</a>"
        ) 