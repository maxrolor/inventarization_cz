# from app.core.database import async_session_maker   # закомментировать
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

sync_engine = create_engine(
    settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)

def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()