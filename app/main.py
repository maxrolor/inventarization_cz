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
    yield
    logger.info("Завершение работы приложения")

app = FastAPI(
    title="Инвентаризация Честный Знак",
    version="1.0.0",
    lifespan=lifespan,
)

# Импорт роутеров (все префиксы заданы внутри роутеров, кроме новых)
from app.api.v1.auth import router as auth_router
from app.api.v1.clients import router as clients_router
from app.api.v1.pages import router as pages_router
from app.api.v1.db_admin import router as db_admin_router
from app.api.v1.client_auth import router as client_auth_router
from app.api.v1.proxy import router as proxy_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.balances import router as balances_router
from app.api.v1.marks import router as marks_router

# Подключение роутеров (без лишних префиксов, т.к. они уже заданы внутри)
app.include_router(auth_router)          # внутри prefix="/auth"
app.include_router(clients_router)       # внутри prefix="/clients"
app.include_router(pages_router)         # внутри prefix="/pages"
app.include_router(db_admin_router)      # внутри prefix="/db-admin"
app.include_router(client_auth_router)   # внутри prefix="/client"
app.include_router(proxy_router)         # внутри prefix="/api/v1/proxy"

# Новые роутеры – добавляем префиксы, чтобы избежать конфликтов
app.include_router(inventory_router, prefix="/inventory")
app.include_router(balances_router, prefix="/balances")
app.include_router(marks_router, prefix="/marks")

# Монтируем статику из папки app/static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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