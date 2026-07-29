import hashlib
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user_device import UserDevice
from app.models.user import User
from app.models.password_reset import PasswordReset
from app.services.email_service import send_reset_code_email
import logging

logger = logging.getLogger(__name__)

def get_device_hash(request) -> str:
    """Вычисляет хэш устройства на основе IP и User-Agent"""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    combined = f"{ip}|{ua}"
    return hashlib.sha256(combined.encode()).hexdigest()

async def is_device_trusted(user_id: int, device_hash: str, db: AsyncSession) -> bool:
    """Проверяет, подтверждено ли устройство для пользователя"""
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == user_id,
            UserDevice.device_hash == device_hash,
            UserDevice.confirmed == True
        )
    )
    return result.scalar_one_or_none() is not None

async def send_verification_code(user: User, db: AsyncSession) -> str:
    """Генерирует код подтверждения, сохраняет и отправляет на email"""
    code = f"{random.randint(100000, 999999)}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    # Используем таблицу password_resets для хранения кодов подтверждения
    # (можно создать отдельную таблицу, но для простоты используем существующую)
    reset = PasswordReset(
        user_id=user.id,
        code=code,
        expires_at=expires,
        used=False
    )
    db.add(reset)
    await db.commit()

    # Отправка email
    await send_reset_code_email(user.email, code, subject="Код подтверждения входа")
    logger.info(f"Код подтверждения отправлен на {user.email}")

    return code

async def verify_verification_code(user_id: int, code: str, db: AsyncSession) -> bool:
    """Проверяет код подтверждения и помечает его использованным"""
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.user_id == user_id,   # user_id - int
            PasswordReset.code == code,
            PasswordReset.used == False,
            PasswordReset.expires_at > datetime.now(timezone.utc)
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        return False
    reset.used = True
    await db.commit()
    return True

async def confirm_device(user_id: int, device_hash: str, db: AsyncSession):
    """Подтверждает устройство (создаёт запись или обновляет)"""
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == user_id,
            UserDevice.device_hash == device_hash
        )
    )
    device = result.scalar_one_or_none()
    if device:
        device.confirmed = True
        device.updated_at = datetime.now(timezone.utc)
    else:
        device = UserDevice(
            user_id=user_id,
            device_hash=device_hash,
            confirmed=True
        )
        db.add(device)
    await db.commit()
    logger.info(f"Устройство подтверждено для пользователя {user_id}")