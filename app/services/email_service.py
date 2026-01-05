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
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #4a4a4a;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px 20px;
                }}
                .email-wrapper {{
                    max-width: 600px;
                    margin: 0 auto;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 2px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    font-size: 28px;
                    font-weight: 600;
                    margin: 0;
                    letter-spacing: -0.5px;
                }}
                .content {{
                    padding: 40px 30px;
                    background-color: #ffffff;
                }}
                .content p {{
                    margin: 0 0 16px 0;
                    color: #4a4a4a;
                    font-size: 15px;
                }}
                .content p:last-of-type {{
                    margin-bottom: 0;
                }}
                .greeting {{
                    font-size: 16px;
                    font-weight: 500;
                    color: #333;
                    margin-bottom: 20px !important;
                }}
                .button-container {{
                    text-align: center;
                    margin: 32px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 2px;
                    font-weight: 500;
                    font-size: 16px;
                    transition: transform 0.2s, box-shadow 0.2s;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                }}
                .button:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
                }}
                .link-section {{
                    background-color: #f8f9fa;
                    border-radius: 2px;
                    padding: 20px;
                    margin: 24px 0;
                }}
                .link-section p {{
                    font-size: 13px;
                    color: #666;
                    margin-bottom: 8px;
                }}
                .reset-link {{
                    word-break: break-all;
                    color: #667eea;
                    font-size: 13px;
                    text-decoration: none;
                    display: block;
                    margin-top: 8px;
                }}
                .warning {{
                    background: linear-gradient(to right, #fff3cd 0%, #fff8e1 100%);
                    border-left: 4px solid #ffc107;
                    border-radius: 2px;
                    padding: 16px 20px;
                    margin: 24px 0;
                }}
                .warning p {{
                    color: #856404;
                    font-size: 14px;
                    margin: 0;
                }}
                .info-box {{
                    background-color: #e8f4fd;
                    border-left: 4px solid #667eea;
                    border-radius: 2px;
                    padding: 16px 20px;
                    margin: 24px 0;
                }}
                .info-box p {{
                    color: #1e3a5f;
                    font-size: 14px;
                    margin: 0;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    text-align: center;
                    padding: 30px;
                    border-top: 1px solid #e9ecef;
                }}
                .footer p {{
                    color: #6c757d;
                    font-size: 13px;
                    margin: 8px 0;
                }}
                .footer-brand {{
                    font-weight: 600;
                    color: #667eea;
                    font-size: 14px;
                }}
                .divider {{
                    height: 1px;
                    background: linear-gradient(to right, transparent, #e9ecef, transparent);
                    margin: 24px 0;
                }}
                @media only screen and (max-width: 600px) {{
                    body {{
                        padding: 20px 10px;
                    }}
                    .header {{
                        padding: 30px 20px;
                    }}
                    .header h1 {{
                        font-size: 24px;
                    }}
                    .content {{
                        padding: 30px 20px;
                    }}
                    .button {{
                        padding: 12px 30px;
                        font-size: 15px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <div class="container">
                    <div class="header">
                        <h1>🔐 Сброс пароля</h1>
                    </div>
                    <div class="content">
                        <p class="greeting">Здравствуйте!</p>

                        <p>Обнаружена попытка сброса пароля вашей учетной записи.</p>

                        <p>Для создания нового пароля нажмите на кнопку ниже:</p>

                        <div class="button-container">
                            <a href="{reset_url}" class="button">Продолжить смену пароля</a>
                        </div>

                        <div class="link-section">
                            <p>Или скопируйте и вставьте эту ссылку в браузер:</p>
                            <a href="{reset_url}" class="reset-link">{reset_url}</a>
                        </div>

                        <div class="warning">
                            <p>Ссылка действительна в течение <strong>1 часа</strong> с момента запроса.</p>
                        </div>

                        <div class="divider"></div>

                        <div class="info-box">
                            <p>Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо. Ваш пароль останется без изменений, и никаких действий предпринимать не нужно.</p>
                        </div>
                    </div>
                    <div class="footer">
                        <p class="footer-brand">© 2025 Comanaso</p>
                        <p>Это автоматическое письмо, пожалуйста, не отвечайте на него.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def _create_reset_password_text(reset_url: str) -> str:
        """Создает текстовую версию письма для сброса пароля."""
        return f"""
╔══════════════════════════════════════════════════════════╗
║              🔐 СБРОС ПАРОЛЯ - COMANASO                 ║
╚══════════════════════════════════════════════════════════╝

Здравствуйте!

Обнаружена попытка сброса пароля вашей учетной записи.

┌──────────────────────────────────────────────────────────┐
│ Для создания нового пароля перейдите по ссылке:         │
└──────────────────────────────────────────────────────────┘

{reset_url}

┌──────────────────────────────────────────────────────────┐
│ ⚠️  ВАЖНАЯ ИНФОРМАЦИЯ                                    │
├──────────────────────────────────────────────────────────┤
│ • Ссылка действительна в течение 1 ЧАСА                 │
│ • После использования ссылка станет недействительной     │
└──────────────────────────────────────────────────────────┘

Если вы не запрашивали сброс пароля, просто проигнорируйте
это письмо. Ваш пароль останется без изменений.

───────────────────────────────────────────────────────────

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
                message["X-Priority"] = "1"

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
                logger.error(
                    f"SMTP error sending password reset email to {to_email} (attempt {attempt}/{max_retries}): {str(e)}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} attempts failed for {to_email}")
                    return False
            except Exception as e:
                logger.error(
                    f"Failed to send password reset email to {to_email} (attempt {attempt}/{max_retries}): {str(e)}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} attempts failed for {to_email}")
                    return False

        return False
