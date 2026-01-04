"""
Сервис для отправки email уведомлений.
Использует Яндекс SMTP для отправки писем.
"""
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Сервис для отправки email через Яндекс SMTP."""

    @staticmethod
    def _create_reset_password_html(reset_url: str) -> str:
        """Создает HTML шаблон письма для сброса пароля."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; }}
                .button {{ 
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .warning {{ 
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Сброс пароля - Comanaso</h1>
                </div>
                <div class="content">
                    <p>Здравствуйте!</p>
                    <p>Вы запросили сброс пароля для вашего аккаунта в системе Comanaso.</p>
                    <p>Для создания нового пароля нажмите на кнопку ниже:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Сбросить пароль</a>
                    </p>
                    <p>Или скопируйте ссылку в браузер:</p>
                    <p style="word-break: break-all; color: #666;">{reset_url}</p>
                    <div class="warning">
                        <strong>⚠️ Важно:</strong> Ссылка действительна в течение 1 часа.
                    </div>
                    <p>Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо. 
                       Ваш пароль останется без изменений.</p>
                </div>
                <div class="footer">
                    <p>© 2025 Comanaso</p>
                    <p>Это автоматическое письмо, не отвечайте на него.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def _create_reset_password_text(reset_url: str) -> str:
        """Создает текстовую версию письма для сброса пароля."""
        return f"""
Сброс пароля - Comanaso

Вы запросили сброс пароля для вашего аккаунта.

Для создания нового пароля перейдите по ссылке:
{reset_url}

⚠️ Важно: Ссылка действительна в течение 1 часа.

Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.

---
© 2025 Comanaso
Это автоматическое письмо, не отвечайте на него.
        """

    @staticmethod
    async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
        """
        Отправляет email со ссылкой для сброса пароля с повторными попытками.

        Args:
            to_email: Email получателя
            reset_token: Токен для сброса пароля

        Returns:
            bool: True если письмо отправлено успешно, False в противном случае
        """
        import asyncio
        from email.utils import formatdate, make_msgid

        max_retries = 3
        retry_delay = 2  # секунды между попытками

        for attempt in range(1, max_retries + 1):
            try:
                # Формируем URL для сброса пароля
                reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

                # Создаем сообщение
                message = MIMEMultipart("alternative")
                message["Subject"] = "Сброс пароля - Comanaso"
                message["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
                message["To"] = to_email
                message["Reply-To"] = settings.smtp_user
                message["Date"] = formatdate(localtime=True)
                message["Message-ID"] = make_msgid(domain=settings.smtp_user.split("@")[1])
                message["X-Mailer"] = "Comanaso Password Reset Service"

                logger.info(f"Preparing password reset email for {to_email} (attempt {attempt}/{max_retries})")
                logger.info(f"Reset URL: {reset_url}")

                # Добавляем текстовую и HTML версии
                text_part = MIMEText(
                    EmailService._create_reset_password_text(reset_url),
                    "plain",
                    "utf-8"
                )
                html_part = MIMEText(
                    EmailService._create_reset_password_html(reset_url),
                    "html",
                    "utf-8"
                )

                message.attach(text_part)
                message.attach(html_part)

                # Подключаемся к SMTP серверу асинхронно
                logger.info(f"Connecting to SMTP: {settings.smtp_host}:{settings.smtp_port}")

                await aiosmtplib.send(
                    message,
                    hostname=settings.smtp_host,
                    port=settings.smtp_port,
                    username=settings.smtp_user,
                    password=settings.smtp_password,
                    use_tls=True,
                    timeout=60  # Увеличен таймаут до 60 секунд
                )

                logger.info(f"Password reset email sent successfully to {to_email}")
                return True

            except aiosmtplib.SMTPException as e:
                logger.error(f"SMTP error sending password reset email to {to_email} (attempt {attempt}/{max_retries}): {str(e)}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} attempts failed for {to_email}")
                    return False
            except Exception as e:
                logger.error(f"Failed to send password reset email to {to_email} (attempt {attempt}/{max_retries}): {str(e)}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} attempts failed for {to_email}")
                    return False

        return False