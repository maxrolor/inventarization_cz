from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.user import User, UserRole  # импорт модели User
from app.models.client import Client  # для полноты
from app.core.security import get_password_hash
from app.services.address_service import clear_address_cache
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/db-admin", tags=["database"])


class DBCheckResult(BaseModel):
    connection_ok: bool
    database_exists: bool
    databases: List[str]
    current_db: str
    tables: List[str]
    error: Optional[str] = None


class CreateDBRequest(BaseModel):
    db_name: str


# Новая модель для создания администратора
class CreateAdminRequest(BaseModel):
    username: str
    password: str
    email: str
    phone: str


@router.get("/check")
async def check_database():
    result = DBCheckResult(
        connection_ok=False,
        database_exists=False,
        databases=[],
        current_db=settings.db_name,
        tables=[]
    )

    system_conn_str = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/postgres"
    system_engine = create_async_engine(system_conn_str, pool_pre_ping=True)

    try:
        async with system_engine.connect() as conn:
            db_list = await conn.execute(text("""
                SELECT datname FROM pg_database 
                WHERE datistemplate = false 
                ORDER BY datname
            """))
            databases = [row[0] for row in db_list]
            result.databases = databases
            result.connection_ok = True
            logger.info(f"Подключение к PostgreSQL успешно. Найдено БД: {len(databases)}")

        if settings.db_name in result.databases:
            result.database_exists = True
            logger.info(f"База данных '{settings.db_name}' существует")
            try:
                async with engine.connect() as conn:
                    tables_result = await conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        ORDER BY table_name
                    """))
                    result.tables = [row[0] for row in tables_result]
                    logger.info(f"Найдено таблиц: {len(result.tables)}")
            except Exception as e:
                logger.error(f"Ошибка при получении списка таблиц: {e}")
                result.error = f"Ошибка при получении списка таблиц: {str(e)}"
        else:
            logger.warning(f"База данных '{settings.db_name}' не существует")

    except Exception as e:
        logger.error(f"Ошибка подключения к PostgreSQL: {e}")
        result.error = f"Ошибка подключения к PostgreSQL: {str(e)}"
    finally:
        await system_engine.dispose()

    return result


@router.post("/create-database")
async def create_database(request: CreateDBRequest):
    system_conn_str = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/postgres"
    system_engine = create_async_engine(
        system_conn_str,
        isolation_level='AUTOCOMMIT',
        pool_pre_ping=True
    )

    try:
        async with system_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": request.db_name}
            )
            if result.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail=f"База данных '{request.db_name}' уже существует"
                )

            await conn.execute(text(f'CREATE DATABASE "{request.db_name}"'))
            logger.info(f"Создана база данных: {request.db_name}")

        new_db_url = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{request.db_name}"
        new_engine = create_async_engine(new_db_url)
        try:
            async with new_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info(f"Таблицы созданы в новой БД: {request.db_name}")
        finally:
            await new_engine.dispose()

        return {
            "status": "success",
            "message": f"База данных '{request.db_name}' создана, таблицы созданы"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании БД/таблиц: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании БД: {str(e)}")
    finally:
        await system_engine.dispose()


@router.get("/admin-exists")
async def admin_exists():
    try:
        async with engine.connect() as conn:
            table_check = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    )
                """)
            )
            if not table_check.scalar():
                return {"exists": False}

            # Исправлено: 'ADMIN' (заглавные)
            result = await conn.execute(
                text("SELECT COUNT(*) FROM users WHERE role = 'ADMIN'")
            )
            count = result.scalar()
            return {"exists": count > 0}
    except Exception as e:
        logger.error(f"Ошибка при проверке админа: {e}")
        return {"exists": False}


@router.post("/create-admin")
async def create_admin(request: CreateAdminRequest):  # принимаем Pydantic модель
    try:
        async with engine.connect() as conn:
            table_check = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    )
                """)
            )
            if not table_check.scalar():
                raise HTTPException(
                    status_code=400,
                    detail="Таблица пользователей не существует. Сначала создайте таблицы."
                )

            # Исправлено: 'ADMIN'
            result = await conn.execute(
                text("SELECT COUNT(*) FROM users WHERE role = 'ADMIN'")
            )
            count = result.scalar()
            if count > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Администратор уже существует"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при проверке админа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка проверки админа")

    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(User).where(
                (User.username == request.username) |
                (User.email == request.email) |
                (User.phone == request.phone)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким именем, email или телефоном уже существует"
            )

        hashed_password = get_password_hash(request.password)
        new_admin = User(
            username=request.username,
            email=request.email,
            phone=request.phone,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,  # теперь это "ADMIN"
            is_active=True
        )
        db.add(new_admin)
        await db.commit()
        logger.info(f"Создан первый администратор: {request.username}")

        return {
            "status": "success",
            "message": "Администратор создан",
            "username": request.username
        }


@router.post("/clear-address-cache")
async def clear_cache():
    clear_address_cache()
    return {"status": "ok"}