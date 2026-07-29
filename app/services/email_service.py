import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_reset_code_email(to_email: str, code: str, subject: str = "Восстановление пароля") -> bool:
    try:
        html = f"""
        <html>
        <body>
            <h2>{subject}</h2>
            <p>Ваш код:</p>
            <h1 style="color: #2d89ef; font-size: 32px; letter-spacing: 4px;">{code}</h1>
            <p>Код действует 15 минут.</p>
            <p>Если вы не запрашивали действие, проигнорируйте это письмо.</p>
            <hr>
            <p style="color: #888; font-size: 12px;">Инвентаризация Честный ЗНАК</p>
        </body>
        </html>
        """
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info(f"Письмо с кодом отправлено на {to_email} (тема: {subject})")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки email на {to_email}: {e}")
        return False

async def send_confirmation_email(to_email: str, token: str) -> bool:
    """Отправка ссылки для подтверждения email"""
    link = f"http://localhost:8000/client/confirm-email?token={token}"
    subject = "Подтверждение email"
    html = f"""
    <html>
    <body>
        <h2>Подтверждение регистрации</h2>
        <p>Для завершения регистрации перейдите по ссылке:</p>
        <p><a href="{link}">{link}</a></p>
        <p>Ссылка действительна 24 часа.</p>
        <p>Если вы не регистрировались, проигнорируйте это письмо.</p>
        <hr>
        <p style="color: #888; font-size: 12px;">Инвентаризация Честный ЗНАК</p>
    </body>
    </html>
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info(f"Письмо с подтверждением отправлено на {to_email}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки подтверждения на {to_email}: {e}")
        return False