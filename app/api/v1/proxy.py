from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import httpx
from typing import Optional
from app.core.config import settings
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/proxy", tags=["proxy"])

class SimpleSignInRequest(BaseModel):
    uuid: str
    data: str          # подписанные данные в base64
    inn: Optional[str] = None
    unitedToken: bool = False

@router.post("/auth-key")
async def proxy_auth_key(
    current_user: User = Depends(get_current_user)
):
    """
    Проксирует запрос GET /auth/key к API Честного знака.
    """
    url = f"{settings.cz_api_base_url}/auth/key"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text or "Ошибка при получении ключа"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Не удалось связаться с API ЧЗ: {str(e)}"
            )

@router.post("/auth-simple-sign-in")
async def proxy_simple_sign_in(
    payload: SimpleSignInRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Проксирует запрос POST /auth/simpleSignIn к API Честного знака.
    """
    url = f"{settings.cz_api_base_url}/auth/simpleSignIn"
    request_body = payload.dict(exclude_none=True)
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                url,
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Прокидываем ошибку с деталями
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text or "Ошибка аутентификации"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Не удалось связаться с API ЧЗ: {str(e)}"
            )