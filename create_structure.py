import os
from pathlib import Path

def create_project_structure(base_path="."):
    """
    Создаёт структуру проекта inventarization_cz.
    Существующие файлы и папки не перезаписываются и не удаляются.
    """
    root = Path(base_path).resolve()
    print(f"📁 Создаю структуру в: {root}")

    # -------- 1. ОПРЕДЕЛЯЕМ СТРУКТУРУ --------
    folders = [
        "alembic/versions",
        "logs",
        "app/api/v1",
        "app/core",
        "app/models",
        "app/schemas",
        "app/services",
        "app/templates/admin",
        "app/templates/cabinet",
        "app/static/css",
        "app/static/js",
        "app/utils",
        "tests",
        "venv",  # папка виртуального окружения (обычно не создаём, но оставим для полноты)
    ]

    files = {
        # Корневые файлы
        ".env": """# Переменные окружения
DATABASE_URL=postgresql://user:password@localhost/inventarization
SECRET_KEY=change_this_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
""",
        ".gitignore": """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv
*.log
.env
.DS_Store
*.db
*.sqlite3
alembic/versions/*.py
!alembic/versions/__init__.py
""",
        "requirements.txt": """fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.25.1
jinja2==3.1.2
aiofiles==23.2.1
""",
        "README.md": "# inventarization_cz\n\nПроект для инвентаризации марок в Честном знаке.\n",

        # Файлы в app/
        "app/__init__.py": "",
        "app/main.py": """from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.api.v1 import health, auth, clients, cabinet

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Роутеры
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(cabinet.router, prefix="/api/v1/cabinet", tags=["cabinet"])

@app.get("/")
async def root():
    return {"message": "Inventarization API"}
""",

        # API роутеры
        "app/api/__init__.py": "",
        "app/api/v1/__init__.py": "",
        "app/api/v1/health.py": """from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "ok"}
""",
        "app/api/v1/auth.py": """from fastapi import APIRouter, Depends, HTTPException
from app.core.security import create_access_token, verify_password
from app.models.user import User
# ... остальной код будет дописан позже

router = APIRouter()

@router.post("/login")
async def login():
    # заглушка
    return {"access_token": "fake-token"}
""",
        "app/api/v1/clients.py": """from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_clients():
    return {"clients": []}
""",
        "app/api/v1/cabinet.py": """from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def dashboard():
    return {"message": "Личный кабинет"}
""",

        # Core
        "app/core/__init__.py": "",
        "app/core/config.py": """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Inventarization CZ"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
""",
        "app/core/database.py": """from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
""",
        "app/core/logging_config.py": """import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "formatter": "default",
            "level": "INFO",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
""",
        "app/core/security.py": """from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
""",
        "app/core/dependencies.py": """from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.core.config import settings
# ... реализация позже

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # заглушка
    return {"id": 1, "username": "test"}
""",

        # Модели
        "app/models/__init__.py": "",
        "app/models/user.py": """from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
""",
        "app/models/client.py": """from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    inn = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
""",
        "app/models/mark_balance.py": """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class MarkBalance(Base):
    __tablename__ = "marks_balance"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    gtin = Column(String, index=True)
    total_quantity = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    client = relationship("Client")
""",
        "app/models/mark_available.py": """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class MarkAvailable(Base):
    __tablename__ = "marks_available"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    serial_number = Column(String, unique=True, index=True)
    status = Column(String, default="available")  # available, used, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client = relationship("Client")
""",
        "app/models/inventory.py": """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Inventory(Base):
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    product_name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client = relationship("Client")
""",

        # Схемы
        "app/schemas/__init__.py": "",
        "app/schemas/user.py": """from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
""",
        "app/schemas/client.py": """from pydantic import BaseModel

class ClientCreate(BaseModel):
    name: str
    inn: str

class ClientOut(BaseModel):
    id: int
    name: str
    inn: str
    is_active: bool
""",
        "app/schemas/mark.py": """from pydantic import BaseModel

class MarkBalanceOut(BaseModel):
    gtin: str
    total_quantity: int
""",
        "app/schemas/inventory.py": """from pydantic import BaseModel

class InventoryOut(BaseModel):
    product_name: str
    quantity: int
    price: float
""",

        # Сервисы
        "app/services/__init__.py": "",
        "app/services/inn_parser.py": """import httpx
from app.core.config import settings

async def get_company_info_by_inn(inn: str):
    # заглушка, позже реализуем запрос к DaData
    return {"name": "ООО Ромашка", "inn": inn}
""",

        # Шаблоны
        "app/templates/base.html": """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Инвентаризация{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/custom.css">
</head>
<body>
    <nav>
        <a href="/">Главная</a>
        <a href="/api/v1/cabinet/dashboard">Кабинет</a>
    </nav>
    <main>
        {% block content %}{% endblock %}
    </main>
    <script src="/static/js/main.js"></script>
</body>
</html>
""",
        "app/templates/login.html": """{% extends "base.html" %}
{% block title %}Вход{% endblock %}
{% block content %}
<h2>Вход</h2>
<form method="post">
    <input type="email" name="email" placeholder="Email">
    <input type="password" name="password" placeholder="Пароль">
    <button type="submit">Войти</button>
</form>
{% endblock %}
""",
        "app/templates/admin/clients.html": """{% extends "base.html" %}
{% block title %}Клиенты{% endblock %}
{% block content %}
<h1>Список клиентов</h1>
<ul>
    <li>Клиент 1</li>
    <li>Клиент 2</li>
</ul>
{% endblock %}
""",
        "app/templates/admin/client_form.html": """{% extends "base.html" %}
{% block title %}Новый клиент{% endblock %}
{% block content %}
<h1>Добавить клиента</h1>
<form method="post">
    <input name="name" placeholder="Название">
    <input name="inn" placeholder="ИНН">
    <button type="submit">Создать</button>
</form>
{% endblock %}
""",
        "app/templates/cabinet/index.html": """{% extends "base.html" %}
{% block title %}Личный кабинет{% endblock %}
{% block content %}
<h1>Добро пожаловать в личный кабинет</h1>
{% endblock %}
""",
        "app/templates/cabinet/marks_balance.html": """{% extends "base.html" %}
{% block title %}Остатки марок{% endblock %}
{% block content %}
<h1>Остатки</h1>
{% endblock %}
""",
        "app/templates/cabinet/marks_available.html": """{% extends "base.html" %}
{% block title %}Марки в наличии{% endblock %}
{% block content %}
<h1>В наличии</h1>
{% endblock %}
""",
        "app/templates/cabinet/inventory.html": """{% extends "base.html" %}
{% block title %}Инвентаризация{% endblock %}
{% block content %}
<h1>Инвентаризация</h1>
{% endblock %}
""",

        # Статика
        "app/static/css/custom.css": "/* ваш CSS */\n",
        "app/static/js/main.js": "// ваш JS\n",

        # Утилиты
        "app/utils/__init__.py": "",
        "app/utils/validators.py": """import re

def validate_inn(inn: str) -> bool:
    # простая проверка длины
    return len(inn) in (10, 12) and inn.isdigit()
""",

        # Миграции
        "alembic/env.py": """from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.database import Base
from app.core.config import settings

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=settings.DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""",
        "alembic/versions/__init__.py": "",  # чтобы папка стала пакетом

        # Тесты (пока пустые)
        "tests/__init__.py": "",
        "tests/test_main.py": """def test_dummy():
    assert True
""",

        # Логи (файл будет создан позже, но папка уже есть)
        "logs/app.log": "",  # пустой файл, будет перезаписан при логировании
    }

    # -------- 2. СОЗДАЁМ ПАПКИ --------
    print("📂 Создаю папки...")
    for folder in folders:
        dir_path = root / folder
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {folder}")
        else:
            print(f"  ⏭️ {folder} уже существует")

    # -------- 3. СОЗДАЁМ ФАЙЛЫ (ТОЛЬКО ЕСЛИ ОТСУТСТВУЮТ) --------
    print("📄 Создаю файлы...")
    for file_path, content in files.items():
        full_path = root / file_path
        if not full_path.exists():
            # Убеждаемся, что родительская папка есть
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ {file_path}")
        else:
            print(f"  ⏭️ {file_path} уже существует")

    print("\n✨ Структура проекта успешно создана!")
    print(f"📌 Рабочая директория: {root}")

if __name__ == "__main__":
    # Можно указать путь, например: python setup.py /path/to/project
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    create_project_structure(base)