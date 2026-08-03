"""
Асинхронный клиент для True API Честного знака.
Использует токен, сохранённый в БД для организации (client_id).
"""
import asyncio
import httpx
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.token_service import TokenService
from app.core.config import settings

logger = logging.getLogger(__name__)


class NoTokenError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


class CzApiClient:
    def __init__(
        self,
        client_id: int,
        db: AsyncSession,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.client_id = client_id
        self.db = db
        self.base_url = base_url or settings.cz_api_base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._token: Optional[str] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._http_client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Accept": "*/*", "Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client:
            await self._http_client.aclose()

    async def _ensure_token(self):
        if self._token is None:
            self._token = await TokenService.get_cz_token(self.client_id, self.db)
            if not self._token:
                raise NoTokenError(
                    "Токен Честного знака не найден для вашей организации. "
                    "Пожалуйста, получите токен через страницу авторизации."
                )

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        await self._ensure_token()

        url = f"{self.base_url}{path}"
        default_headers = {"Authorization": f"Bearer {self._token}"}
        if headers:
            default_headers.update(headers)

        for attempt in range(self.max_retries):
            try:
                response = await self._http_client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    data=data,
                    headers=default_headers,
                )
                if response.status_code == 401:
                    raise TokenExpiredError(
                        "Токен Честного знака истёк. Обновите его через страницу авторизации."
                    )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 500, 502, 503):
                    wait = 2 ** attempt
                    logger.warning(f"Retry {attempt+1}/{self.max_retries} after {wait}s")
                    await asyncio.sleep(wait)
                    continue
                raise
            except (TokenExpiredError, NoTokenError):
                raise
        raise RuntimeError("Max retries exceeded")

    # ---------- Методы API ----------

    async def get_cises_info(self, cises: List[str]) -> Dict[str, Any]:
        """Получение информации о кодах маркировки."""
        path = "/api/v3/true-api/cises/info"
        response = await self._request("POST", path, json_data=cises)
        return response.json()

    async def create_document(
        self,
        pg: str,
        doc_type: str,
        product_document: Dict[str, Any],
        document_format: str = "MANUAL",
        second_product_document: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Создание документа в Честном знаке."""
        # Здесь должна быть логика создания документа
        # (пока заглушка, будет доработана позже)
        raise NotImplementedError("Метод create_document будет реализован позже")

    # ... другие методы (create_write_off, create_report_reweighing и т.д.)