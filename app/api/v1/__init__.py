from fastapi import APIRouter

from .auth import router as auth_router
from .cabinet import router as cabinet_router
from .client_auth import router as client_auth_router
from .clients import router as clients_router
from .db_admin import router as db_admin_router
from .health import router as health_router
from .pages import router as pages_router
from .proxy import router as proxy_router

# Создаем главный роутер для версии v1
router = APIRouter(prefix="/api/v1")

# Подключаем все под-роутеры
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(cabinet_router, prefix="/cabinet", tags=["cabinet"])
router.include_router(client_auth_router, prefix="/client-auth", tags=["client-auth"])
router.include_router(clients_router, prefix="/clients", tags=["clients"])
router.include_router(db_admin_router, prefix="/db-admin", tags=["db-admin"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(pages_router, prefix="/pages", tags=["pages"])
router.include_router(proxy_router, tags=["proxy"])   # <-- убрали prefix, т.к. он уже есть в роутере