from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.client import Client, ClientType
from app.models.client_address import ClientAddress
from app.schemas.client import ClientCreate, ClientLogin, ClientResponse, ClientUpdate
from app.services.inn_parser import INNParser
from app.services.address_service import suggest_addresses
from app.services.email_service import send_confirmation_email
from app.core.dependencies import get_current_client
import logging
from datetime import date
import secrets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/client", tags=["client"])
templates = Jinja2Templates(directory="app/templates")


# ---- Страницы (GET) ----
@router.get("/login", response_class=HTMLResponse)
async def client_login_page(request: Request):
    return templates.TemplateResponse("client/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def client_register_page(request: Request):
    return templates.TemplateResponse("client/register.html", {"request": request})


@router.get("/profile", response_class=HTMLResponse)
async def client_profile_page(
    request: Request,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == current_user.client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    result = await db.execute(select(ClientAddress).where(ClientAddress.client_id == client.id))
    addresses = result.scalars().all()
    return templates.TemplateResponse(
        "client/profile.html",
        {
            "request": request,
            "client": client,
            "addresses": addresses,
            "today": date.today()
        }
    )


@router.get("/confirm-email", response_class=HTMLResponse)
async def confirm_email(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.confirmation_token == token))
    client = result.scalar_one_or_none()
    if not client:
        return templates.TemplateResponse(
            "client/confirm_email.html",
            {"request": request, "success": False, "message": "Неверный или просроченный токен"}
        )
    client.email_confirmed = True
    client.confirmation_token = None
    await db.commit()
    return templates.TemplateResponse(
        "client/confirm_email.html",
        {"request": request, "success": True, "message": "Email успешно подтверждён"}
    )


# ---- API для парсинга ИНН ----
@router.get("/parse-inn")
async def parse_inn(inn: str):
    parser = INNParser()
    data = await parser.get_company_info(inn)
    if not data:
        raise HTTPException(status_code=404, detail="ИНН не найден")
    return data


# ---- API для подсказок адресов ----
@router.get("/suggest-address")
async def suggest_address(query: str, count: int = 10):
    return await suggest_addresses(query, count)


# ---- API-эндпоинты регистрации/входа/обновления ----
@router.post("/register", response_model=ClientResponse)
async def register_client(
    data: ClientCreate,
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Получены данные для регистрации: {data}")

    # Проверка на дублирование ИНН
    result = await db.execute(select(Client).where(Client.inn == data.inn))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Клиент с таким ИНН уже зарегистрирован")

    # Проверка email в User (уникальность)
    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email уже используется")

    # Парсинг ИНН (заполнение данных)
    parser = INNParser()
    company_data = await parser.get_company_info(data.inn)
    if not company_data:
        logger.warning(f"Не удалось получить данные по ИНН {data.inn}, используется введённое")
    else:
        data.name = company_data.get("name", data.name)
        data.ceo_name = company_data.get("ceo_name", data.ceo_name)
        if company_data.get("type") == "legal":
            data.type = ClientType.LEGAL
            data.kpp = company_data.get("kpp")
        else:
            data.type = ClientType.INDIVIDUAL
            data.kpp = None

    # Создание пользователя
    hashed_password = get_password_hash(data.password)
    new_user = User(
        username=data.email or data.inn,
        email=data.email,
        phone=data.phone,
        full_name=data.ceo_name,
        hashed_password=hashed_password,
        role=UserRole.CLIENT,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Создание клиента
    new_client = Client(
        inn=data.inn,
        name=data.name,
        ceo_name=data.ceo_name,
        type=data.type,
        kpp=data.kpp,
        phone=data.phone,
        email=data.email,
        is_verified=True if company_data else False,
        is_blocked=False,
        subscription_end_date=None,
        email_confirmed=False,
        confirmation_token=None,
    )
    db.add(new_client)
    await db.flush()

    # Связь пользователя с клиентом
    new_user.client_id = new_client.id

    # Добавление адресов
    for addr in data.addresses:
        if addr.strip():
            client_address = ClientAddress(
                client_id=new_client.id,
                address=addr.strip(),
                is_primary=False,
            )
            db.add(client_address)
    if data.addresses:
        first = await db.execute(
            select(ClientAddress).where(ClientAddress.client_id == new_client.id).order_by(ClientAddress.id).limit(1)
        )
        first_addr = first.scalar_one_or_none()
        if first_addr:
            first_addr.is_primary = True

    # Генерация токена подтверждения
    confirmation_token = secrets.token_urlsafe(32)
    new_client.confirmation_token = confirmation_token

    await db.commit()
    await db.refresh(new_client)

    # Отправка письма с подтверждением
    if data.email:
        await send_confirmation_email(data.email, confirmation_token)

    # Получение адресов для ответа
    result = await db.execute(
        select(ClientAddress.address).where(ClientAddress.client_id == new_client.id)
    )
    addresses = [row[0] for row in result]

    logger.info(f"Зарегистрирован новый клиент: {new_client.inn} ({new_client.name})")
    return ClientResponse(
        **new_client.__dict__,
        addresses=addresses
    )


@router.post("/login")
async def login_client(
    data: ClientLogin,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.inn == data.inn))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=401, detail="Неверный ИНН или пароль")

    result = await db.execute(select(User).where(User.client_id == client.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Учётная запись не найдена")

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный ИНН или пароль")

    if client.is_blocked or not user.is_active:
        raise HTTPException(status_code=403, detail="Учётная запись заблокирована")

    if client.subscription_end_date and client.subscription_end_date < date.today():
        raise HTTPException(status_code=403, detail="Срок подписки истёк")

    if not client.email_confirmed:
        raise HTTPException(status_code=403, detail="Подтвердите email перед входом")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.put("/profile")
async def update_client_profile(
    data: ClientUpdate,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == current_user.client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    if data.phone is not None:
        client.phone = data.phone
    if data.email is not None:
        client.email = data.email
        current_user.email = data.email

    if data.addresses is not None:
        await db.execute(delete(ClientAddress).where(ClientAddress.client_id == client.id))
        for idx, addr in enumerate(data.addresses):
            if addr.strip():
                new_addr = ClientAddress(
                    client_id=client.id,
                    address=addr.strip(),
                    is_primary=(idx == 0)
                )
                db.add(new_addr)

    await db.commit()

    result = await db.execute(select(ClientAddress.address).where(ClientAddress.client_id == client.id))
    addresses = [row[0] for row in result]

    return {
        "id": client.id,
        "phone": client.phone,
        "email": client.email,
        "addresses": addresses,
        "message": "Профиль обновлён"
    }