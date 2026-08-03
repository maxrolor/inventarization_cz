import httpx
from fastapi import APIRouter, HTTPException, Request
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Используем префикс /api/v1/proxy для единообразия с другими API-роутерами
router = APIRouter(prefix="/api/v1/proxy", tags=["proxy"])

CZ_API_BASE = settings.cz_api_base_url
TIMEOUT = settings.cz_api_timeout

@router.get("/auth-key")
async def proxy_auth_key():
    """
    Прокси для получения ключа сессии (auth/key) от API Честного знака.
    """
    url = f"{CZ_API_BASE}/auth/key"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка при запросе к {url}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error(f"Ошибка при запросе к {url}: {str(e)}")
            raise HTTPException(status_code=500, detail="Ошибка прокси-сервера")

@router.post("/auth-simple-sign-in")
async def proxy_auth_simple_sign_in(request: Request):
    """
    Прокси для авторизации (auth/simpleSignIn) с подписью.
    """
    url = f"{CZ_API_BASE}/auth/simpleSignIn"
    body = await request.json()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(url, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка при запросе к {url}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error(f"Ошибка при запросе к {url}: {str(e)}")
            raise HTTPException(status_code=500, detail="Ошибка прокси-сервера")