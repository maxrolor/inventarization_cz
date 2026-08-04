from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.dependencies import get_current_admin, get_current_client, get_current_user
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.client_address import ClientAddress
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pages", tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


# ---- Общие страницы (доступны без авторизации) ----
@router.get("/index", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа администратора. Если пользователь уже авторизован – редирект на профиль."""
    try:
        token = request.cookies.get("access_token")
        if token:
            return RedirectResponse(url="/profile", status_code=302)
    except Exception:
        pass
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request})


# ---- Админские страницы (только для администраторов) ----
@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Client).order_by(Client.id))
    clients = result.scalars().all()
    return templates.TemplateResponse(
        "admin/clients.html",
        {"request": request, "clients": clients}
    )


@router.get("/db-check", response_class=HTMLResponse)
async def db_check_page(
    request: Request,
    admin: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        "db_check.html",
        {
            "request": request,
            "current_db": settings.db_name
        }
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    admin: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        "admin/profile.html",
        {"request": request}
    )


@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    admin: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        "admin/users.html",
        {"request": request}
    )


@router.get("/cz-auth", response_class=HTMLResponse)
async def cz_auth_page(
    request: Request,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Страница получения токена Честного знака.
    Доступна только авторизованным клиентам.
    """
    has_token = False
    expires = None
    if current_user.client_id:
        client = await db.get(Client, current_user.client_id)
        if client:
            has_token = client.cz_token_encrypted is not None
            expires = client.cz_token_expires

    return templates.TemplateResponse(
        "auth/cz_auth.html",
        {
            "request": request,
            "has_token": has_token,
            "expires": expires.isoformat() if expires else None,
        }
    )


# ---- Тестовая страница для API (добавлена) ----
@router.get("/api-test", response_class=HTMLResponse)
async def api_test_page(request: Request):
    return templates.TemplateResponse("client/api_test.html", {"request": request})