from typing import Optional  # <-- добавить эту строку
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_client
from app.models.user import User
from app.services.balance_service import BalanceService

router = APIRouter(tags=["balances"])

@router.get("/")
async def get_balance(
    warehouse_id: Optional[str] = Query(None, description="ID склада (если не указан – все склады)"),
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Получить остатки марок на складах."""
    service = BalanceService(db, current_user.client_id)
    try:
        return await service.get_balance(warehouse_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))