from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.client import Client
from app.models.client_address import ClientAddress
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.services.inn_parser import INNParser
import logging

logger = logging.getLogger(__name__)

# СОЗДАЁМ РОУТЕР
router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=List[ClientResponse])
async def get_clients(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        search: Optional[str] = None,
        admin: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
):
    """Получить список всех клиентов (только для админа)"""
    logger.info(f"Админ {admin.username} запрашивает список клиентов")

    query = select(Client)
    if search:
        query = query.where(
            (Client.name.ilike(f"%{search}%")) |
            (Client.inn.ilike(f"%{search}%"))
        )
    query = query.offset(skip).limit(limit).order_by(Client.id)

    result = await db.execute(query)
    clients = result.scalars().all()

    # Для каждого клиента получаем адреса
    client_ids = [c.id for c in clients]
    if client_ids:
        addr_result = await db.execute(
            select(ClientAddress.client_id, ClientAddress.address)
            .where(ClientAddress.client_id.in_(client_ids))
        )
        # Группируем адреса по client_id
        addresses_map = {}
        for client_id, addr in addr_result:
            addresses_map.setdefault(client_id, []).append(addr)
    else:
        addresses_map = {}

    response = []
    for client in clients:
        response.append(
            ClientResponse(
                id=client.id,
                inn=client.inn,
                name=client.name,
                ceo_name=client.ceo_name,
                type=client.type,
                kpp=client.kpp,
                phone=client.phone,
                email=client.email,
                is_verified=client.is_verified,
                is_blocked=client.is_blocked,
                subscription_end_date=client.subscription_end_date,
                created_at=client.created_at,
                updated_at=client.updated_at,
                email_confirmed=client.email_confirmed,
                addresses=addresses_map.get(client.id, [])
            )
        )

    logger.info(f"Найдено {len(clients)} клиентов")
    return response


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить клиента по ID (только для админа)"""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        logger.warning(f"Клиент с ID {client_id} не найден")
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Получаем адреса
    addr_result = await db.execute(
        select(ClientAddress.address).where(ClientAddress.client_id == client_id)
    )
    addresses = [row[0] for row in addr_result]

    # Собираем ответ вручную
    return ClientResponse(
        id=client.id,
        inn=client.inn,
        name=client.name,
        ceo_name=client.ceo_name,
        type=client.type,
        kpp=client.kpp,
        phone=client.phone,
        email=client.email,
        is_verified=client.is_verified,
        is_blocked=client.is_blocked,
        subscription_end_date=client.subscription_end_date,
        created_at=client.created_at,
        updated_at=client.updated_at,
        email_confirmed=client.email_confirmed,
        addresses=addresses
    )


@router.post("/", response_model=ClientResponse)
async def create_client(
        client_data: ClientCreate,
        admin: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
):
    """Создать нового клиента (только для админа)"""
    # Проверяем, не существует ли клиент с таким ИНН
    result = await db.execute(
        select(Client).where(Client.inn == client_data.inn)
    )
    if result.scalar_one_or_none():
        logger.warning(f"Клиент с ИНН {client_data.inn} уже существует")
        raise HTTPException(
            status_code=400,
            detail="Клиент с таким ИНН уже существует"
        )

    # Создаём клиента
    new_client = Client(**client_data.model_dump())
    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)

    logger.info(f"Админ {admin.username} создал клиента: {new_client.name} (ИНН: {new_client.inn})")
    return new_client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
        client_id: int,
        client_data: ClientUpdate,
        admin: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
):
    """Обновить данные клиента (только для админа)"""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        logger.warning(f"Клиент с ID {client_id} не найден")
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Обновляем только переданные поля
    update_data = client_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    await db.commit()
    await db.refresh(client)

    logger.info(f"Админ {admin.username} обновил клиента ID {client_id}")
    return client


@router.delete("/{client_id}")
async def delete_client(
        client_id: int,
        admin: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
):
    """Удалить клиента (только для админа)"""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        logger.warning(f"Клиент с ID {client_id} не найден")
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Проверяем, есть ли у клиента пользователь
    result = await db.execute(select(User).where(User.client_id == client_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        logger.info(f"Удалён пользователь {user.username} для клиента {client_id}")

    await db.delete(client)
    await db.commit()

    logger.info(f"Админ {admin.username} удалил клиента ID {client_id}")
    return {"message": "Клиент удалён"}


@router.post("/{client_id}/verify")
async def verify_client(
        client_id: int,
        admin: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
):
    """Верифицировать клиента по ИНН (только для админа)"""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    parser = INNParser()
    company_data = await parser.get_company_info(client.inn)

    if company_data:
        client.is_verified = True
        for key, value in company_data.items():
            if hasattr(client, key) and value:
                setattr(client, key, value)

        await db.commit()
        logger.info(f"Клиент {client.name} верифицирован по ИНН {client.inn}")
        return {"status": "verified", "data": company_data}
    else:
        client.is_verified = False
        await db.commit()
        logger.warning(f"Клиент {client.name} не прошёл верификацию по ИНН {client.inn}")
        raise HTTPException(
            status_code=400,
            detail="ИНН не найден в базе ФНС"
        )


@router.post("/{client_id}/block")
async def toggle_block_client(
        client_id: int,
        admin: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
):
    """Блокировка/разблокировка клиента (только для админа)"""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    client.is_blocked = not client.is_blocked
    await db.commit()

    # Блокируем/разблокируем пользователя
    result = await db.execute(select(User).where(User.client_id == client_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_active = not client.is_blocked
        await db.commit()

    status_text = "заблокирован" if client.is_blocked else "разблокирован"
    logger.info(f"Клиент {client.name} {status_text} админом {admin.username}")

    return {
        "client_id": client_id,
        "is_blocked": client.is_blocked,
        "message": f"Клиент {status_text}"
    }


@router.post("/{client_id}/fill-from-inn")
async def fill_client_from_inn(
        client_id: int,
        admin: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
):
    """Заполнить данные клиента по ИНН (только для админа)"""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    parser = INNParser()
    company_data = await parser.get_company_info(client.inn)

    if not company_data:
        raise HTTPException(
            status_code=400,
            detail="Не удалось получить данные по ИНН"
        )

    for key, value in company_data.items():
        if hasattr(client, key) and value:
            setattr(client, key, value)

    await db.commit()
    await db.refresh(client)

    logger.info(f"Данные клиента {client.name} обновлены по ИНН {client.inn}")
    return company_data


@router.post("/confirm-email/{client_id}")
async def confirm_client_email(
    client_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    client.email_confirmed = True
    client.confirmation_token = None
    await db.commit()
    return {"message": "Email подтверждён"}