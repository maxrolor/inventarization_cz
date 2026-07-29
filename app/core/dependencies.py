from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_token_from_request(request: Request) -> str:
    token = request.cookies.get("access_token")
    if token:
        logger.debug("Токен получен из cookie")
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        logger.debug("Токен получен из заголовка Authorization")
        return token

    logger.warning("Токен не найден ни в cookie, ни в заголовке")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Токен не найден",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
        token: str = Depends(get_token_from_request),
        db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if not payload:
        logger.warning("Невалидный токен")
        raise credentials_exception

    sub = payload.get("sub")
    if not sub:
        logger.warning("В токене нет 'sub'")
        raise credentials_exception

    # Преобразуем в int
    try:
        user_id = int(sub)
    except ValueError:
        logger.warning(f"'sub' не является числом: {sub}")
        raise credentials_exception

    logger.debug(f"ID пользователя из токена: {user_id}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"Пользователь с ID {user_id} не найден")
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Учётная запись заблокирована")
    return user


async def get_current_admin(
        current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Пользователь {current_user.username} не админ")
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return current_user


async def get_current_client(
        current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.CLIENT:
        logger.warning(f"Пользователь {current_user.username} не клиент")
        raise HTTPException(status_code=403, detail="Требуются права клиента")
    return current_user