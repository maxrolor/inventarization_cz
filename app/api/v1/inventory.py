from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_client
from app.models.user import User
from app.services.inventory_service import InventoryService
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(tags=["inventory"])

# Pydantic-схемы для запросов
class CreateInventoryRequest(BaseModel):
    warehouse_id: str
    name: Optional[str] = None

class AddMarksRequest(BaseModel):
    marks: List[str]

# --- Эндпоинты ---

@router.post("/")
async def create_inventory(
    data: CreateInventoryRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую инвентаризационную сессию."""
    service = InventoryService(db, current_user.client_id)
    try:
        session = await service.create_session(data.warehouse_id, data.name)
        return {
            "id": session.id,
            "status": session.status,
            "started_at": session.started_at,
            "cz_session_id": session.extra_data.get("cz_session_id") if session.extra_data else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
async def list_inventories(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Получить список сессий инвентаризации (с фильтром по статусу)."""
    service = InventoryService(db, current_user.client_id)
    # Преобразуем строку в enum, если передан
    status_enum = None
    if status:
        try:
            from app.models.inventory import InventorySessionStatus
            status_enum = InventorySessionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Некорректный статус")
    sessions = await service.get_sessions(status_enum)
    return sessions

@router.get("/{session_id}")
async def get_inventory(
    session_id: int,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Получить детали конкретной сессии."""
    service = InventoryService(db, current_user.client_id)
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    return session

@router.post("/{session_id}/marks")
async def add_marks(
    session_id: int,
    data: AddMarksRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Добавить отсканированные марки в сессию."""
    service = InventoryService(db, current_user.client_id)
    try:
        result = await service.add_scanned_marks(session_id, data.marks)
        return {"message": "Марки добавлены", "cz_response": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/finish")
async def finish_inventory(
    session_id: int,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Завершить инвентаризацию (отправить финальный отчёт в ЧЗ)."""
    service = InventoryService(db, current_user.client_id)
    try:
        result = await service.finish_session(session_id)
        return {"message": "Инвентаризация завершена", "cz_response": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/cancel")
async def cancel_inventory(
    session_id: int,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Отменить инвентаризацию (без взаимодействия с ЧЗ)."""
    service = InventoryService(db, current_user.client_id)
    try:
        await service.cancel_session(session_id)
        return {"message": "Инвентаризация отменена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))