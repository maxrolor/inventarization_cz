from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Базовый класс для моделей (все модели будут наследоваться от него)
Base = declarative_base()

# Создаём асинхронный движок
engine = create_async_engine(
    settings.database_url,
    echo=False,                 # Не выводить SQL в консоль (мы контролируем через логгер)
    pool_size=10,               # Размер пула соединений
    max_overflow=20,
    pool_pre_ping=True,         # Проверять соединение перед использованием
    pool_recycle=3600,          # Пересоздавать соединение через час
)

# Фабрика асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Функция для получения сессии в зависимостях FastAPI
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Ошибка при работе с сессией БД: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()