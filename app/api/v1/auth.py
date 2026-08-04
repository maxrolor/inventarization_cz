from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.user import UserRegister, UserResponse, Token
from app.core.dependencies import get_current_user, get_current_admin
from app.services.device_service import (
    get_device_hash,
    is_device_trusted,
    send_verification_code,
    verify_verification_code,
    confirm_device
)
from app.services.token_service import TokenService
import logging
import random
from datetime import datetime, timedelta, timezone
from app.models.password_reset import PasswordReset
from app.schemas.user import ResetPasswordRequest, ResetPasswordVerify
from app.services.email_service import send_reset_code_email

class CZTokenRequest(BaseModel):
    token: str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись заблокирована",
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login-web")
async def login_web(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    from app.api.v1.pages import templates

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"Неудачная попытка входа: {username}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверное имя пользователя или пароль"}
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Учётная запись заблокирована"}
        )

    # Если администратор – проверяем устройство
    if user.role == UserRole.ADMIN:
        device_hash = get_device_hash(request)
        trusted = await is_device_trusted(user.id, device_hash, db)
        if not trusted:
            await send_verification_code(user, db)
            return templates.TemplateResponse(
                "verify_device.html",
                {
                    "request": request,
                    "user_id": user.id,
                    "email": user.email
                }
            )

    # Клиент или админ с подтверждённым устройством – выдаём токен
    access_token = create_access_token(data={"sub": str(user.id)})
    redirect_url = "/pages/admin" if user.role == UserRole.ADMIN else "/client/profile"
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        secure=False,
        samesite="lax",
        path="/",
    )
    logger.info(f"Пользователь {username} вошёл через веб, cookie установлен")
    return response

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Имя пользователя уже занято",
        )
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info(f"Зарегистрирован новый пользователь: {new_user.username}")
    return new_user

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user

@router.get("/debug-cookie")
async def debug_cookie(request: Request):
    return {
        "cookies": dict(request.cookies),
        "headers": dict(request.headers),
    }

@router.post("/request-reset")
async def request_password_reset(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Запрос сброса пароля для email: {data.email}")

    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.info(f"Запрос сброса для несуществующего email: {data.email}")
        return {"message": "Если email зарегистрирован, код отправлен"}

    code = f"{random.randint(100000, 999999)}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    reset_entry = PasswordReset(
        user_id=user.id,
        code=code,
        expires_at=expires,
        used=False
    )
    db.add(reset_entry)
    await db.commit()

    await send_reset_code_email(data.email, code)
    logger.info(f"Код сброса отправлен на {data.email}")

    return {"message": "Код отправлен на вашу почту"}

@router.post("/verify-reset")
async def verify_reset_code(
    data: ResetPasswordVerify,
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Проверка кода для email: {data.email}")

    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.user_id == user.id,
            PasswordReset.code == data.code,
            PasswordReset.used == False,
            PasswordReset.expires_at > datetime.now(timezone.utc)
        )
    )
    reset_entry = result.scalar_one_or_none()
    if not reset_entry:
        raise HTTPException(status_code=400, detail="Неверный или просроченный код")

    new_hashed = get_password_hash(data.new_password)
    user.hashed_password = new_hashed
    reset_entry.used = True
    await db.commit()
    logger.info(f"Пароль изменён для {data.email}")
    return {"message": "Пароль успешно изменён"}

@router.post("/verify-device")
async def verify_device(
    request: Request,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    user_id = data.get("user_id")
    code = data.get("code")
    if not user_id or not code:
        raise HTTPException(status_code=400, detail="Недостаточно данных")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Неверный формат user_id")

    valid = await verify_verification_code(user_id, code, db)
    if not valid:
        raise HTTPException(status_code=400, detail="Неверный или просроченный код")

    device_hash = get_device_hash(request)
    await confirm_device(user_id, device_hash, db)

    access_token = create_access_token(data={"sub": str(user_id)})
    response = JSONResponse(content={
        "message": "Устройство подтверждено, вход выполнен",
        "access_token": access_token
    })
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        secure=False,
        samesite="lax",
        path="/",
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Выход из системы – удаляет cookie с токеном и перенаправляет на главную.
    """
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=False,
        httponly=True,
        samesite="lax"
    )
    logger.info("Пользователь вышел из системы")
    return response

@router.post("/set-cz-token", status_code=status.HTTP_200_OK)
async def set_cz_token(
    request: CZTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Сохраняет токен Честного знака для организации пользователя.
    """
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не привязан к организации."
        )
    try:
        await TokenService.set_cz_token(current_user.client_id, request.token, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok", "message": "Токен сохранён"}

"""
@router.get("/cz-token-status")
async def cz_token_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    #Возвращает статус токена для организации пользователя.
    
    if not current_user.client_id:
        return {"has_token": False, "expires": None}
    client = await db.get(Client, current_user.client_id)
    has_token = client is not None and client.cz_token_encrypted is not None
    expires = client.cz_token_expires.isoformat() if client and client.cz_token_expires else None
    return {
        "has_token": has_token,
        "expires": expires,
    }
"""
