from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker

# Для синхронных задач Celery нам нужен синхронный доступ к БД.
# Мы можем использовать `sync_to_async` или создать отдельный синхронный движок.
# Рекомендуется использовать отдельный синхронный движок, чтобы не смешивать с async-кодом.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Создаём синхронный движок (используем тот же DSN, но без asyncpg)
sync_engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)

def get_sync_db():
    """Генератор сессии для использования в Celery-задачах."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()