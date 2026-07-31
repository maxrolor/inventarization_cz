import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from app.core.config import settings
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

_fernet = Fernet(settings.fernet_key.encode())

# --- Хеширование паролей ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# --- JWT ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    logger.debug(f"Создание токена с secret_key: {settings.secret_key[:5]}...")
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.error(f"Ошибка декодирования токена: {e}")
        return {}

def encrypt_token(token: str) -> str:
    """Шифрует строку токена."""
    return _fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Расшифровывает зашифрованный токен."""
    return _fernet.decrypt(encrypted_token.encode()).decode()