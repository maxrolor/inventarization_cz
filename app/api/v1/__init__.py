from fastapi import APIRouter
from .auth import router as auth_router
from .cabinet import router as cabinet_router
from .client_auth import router as client_auth_router
from .clients import router as clients_router
from .db_admin import router as db_admin_router
from .health import router as health_router
from .pages import router as pages_router
from .proxy import router as proxy_router

# Новые роутеры
from .inventory import router as inventory_router
from .balances import router as balances_router
from .marks import router as marks_router

router = APIRouter(prefix="/api/v1")

# Существующие
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(cabinet_router, prefix="/cabinet", tags=["cabinet"])
router.include_router(client_auth_router, prefix="/client-auth", tags=["client-auth"])
router.include_router(clients_router, prefix="/clients", tags=["clients"])
router.include_router(db_admin_router, prefix="/db-admin", tags=["db-admin"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(pages_router, prefix="/pages", tags=["pages"])
router.include_router(proxy_router, tags=["proxy"])

# Добавляем новые
router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
router.include_router(balances_router, prefix="/balances", tags=["balances"])
router.include_router(marks_router, prefix="/marks", tags=["marks"])