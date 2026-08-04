from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_current_client
from app.models.user import User
from app.services.mark_service import MarkService

router = APIRouter(tags=["marks"])

# Pydantic-схемы для запросов
class ValidateMarksRequest(BaseModel):
    marks: List[str]
    pg: Optional[str] = None

class SearchMarksRequest(BaseModel):
    product_groups: List[str]
    gtins: Optional[List[str]] = None
    emission_date_from: Optional[str] = None
    emission_date_to: Optional[str] = None
    states: Optional[List[dict]] = None
    is_aggregated: bool = False
    per_page: int = 1000

# ---- Эндпоинты ----

@router.post("/validate/full")
async def validate_marks_full(
    data: ValidateMarksRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Полная проверка марок (метод 5.1.2)."""
    service = MarkService(db, current_user.client_id)
    try:
        result = await service.validate_marks_full(data.marks, data.pg)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/validate/short")
async def validate_marks_short(
    data: ValidateMarksRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Упрощённая проверка марок (метод 5.1.3)."""
    service = MarkService(db, current_user.client_id)
    try:
        result = await service.validate_marks_short(data.marks, data.pg)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/validate/minimal")
async def validate_marks_minimal(
    data: ValidateMarksRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Минимальная проверка марок (метод 5.1.4)."""
    service = MarkService(db, current_user.client_id)
    try:
        result = await service.validate_marks_minimal(data.marks, data.pg)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/search")
async def search_marks(
    data: SearchMarksRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Массовый поиск марок с пагинацией (метод 5.1.1)."""
    service = MarkService(db, current_user.client_id)
    try:
        result = await service.search_marks(
            product_groups=data.product_groups,
            gtins=data.gtins,
            emission_date_from=data.emission_date_from,
            emission_date_to=data.emission_date_to,
            states=data.states,
            is_aggregated=data.is_aggregated,
            per_page=data.per_page
        )
        return {"total": len(result), "items": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))