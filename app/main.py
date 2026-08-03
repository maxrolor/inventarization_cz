import logging
import os
from fastapi import FastAPI, Request, status, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from contextlib import asynccontextmanager
from app.core.logging_config import setup_logging
from app.celery_tasks.celery_app import celery_app



setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск приложения...")
    logger.info("Приложение запущено. База данных будет проверена через интерфейс.")
    yield
    logger.info("Завершение работы приложения")

app = FastAPI(
    title="Инвентаризация Честный Знак",
    version="1.0.0",
    lifespan=lifespan,
)

# Импорт роутеров
from app.api.v1.auth import router as auth_router
from app.api.v1.clients import router as clients_router
from app.api.v1.pages import router as pages_router
from app.api.v1.db_admin import router as db_admin_router
from app.api.v1.client_auth import router as client_auth_router

# Подключение роутеров
app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(pages_router)
app.include_router(db_admin_router)
app.include_router(client_auth_router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/pages/index")

@app.get("/profile")
async def profile_redirect(current_user: User = Depends(get_current_user)):
    """Перенаправляет на соответствующий профиль в зависимости от роли"""
    if current_user.role == UserRole.ADMIN:
        return RedirectResponse(url="/pages/profile")
    else:
        return RedirectResponse(url="/client/profile")

# ---- Обработчики ошибок ----
templates = Jinja2Templates(directory="app/templates")

@app.exception_handler(status.HTTP_403_FORBIDDEN)
async def forbidden_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "errors/403.html",
        {"request": request},
        status_code=status.HTTP_403_FORBIDDEN
    )

@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "errors/404.html",
        {"request": request},
        status_code=status.HTTP_404_NOT_FOUND
    )