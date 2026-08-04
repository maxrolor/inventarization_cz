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
        """
        Универсальный метод для выполнения запросов к API.
        path – должен начинаться с '/' и быть относительно self.base_url.
        """
        await self._ensure_token()

        # Формируем полный URL
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
                try:
                    error_body = e.response.text
                except:
                    error_body = "не удалось прочитать"
                logger.error(f"HTTP ошибка {e.response.status_code}: {error_body}")

                if e.response.status_code in (429, 500, 502, 503):
                    wait = 2 ** attempt
                    logger.warning(f"Retry {attempt+1}/{self.max_retries} after {wait}s")
                    await asyncio.sleep(wait)
                    continue
                raise
            except (TokenExpiredError, NoTokenError):
                raise
        raise RuntimeError("Max retries exceeded")

    # ---------- 1. Методы получения информации о КИ ----------
    # Пути взяты из документации.

    async def get_cises_info(
        self, cises: List[str], pg: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение полной информации о КИ по списку (до 1000).
        Метод 5.1.2: /true-api/cises/info
        """
        path = "/true-api/cises/info"
        params = {"pg": pg} if pg else {}
        response = await self._request("POST", path, params=params, json_data=cises)
        return response.json()

    async def get_cises_short_info(
        self, cises: List[str], pg: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Упрощённая информация о КИ (быстрее).
        Метод 5.1.3: /cises/short/list
        """
        path = "/cises/short/list"
        params = {"pg": pg} if pg else {}
        response = await self._request("POST", path, params=params, json_data=cises)
        return response.json()

    async def get_cises_minimal_info(
        self, cises: List[str], pg: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Минимальная информация о КИ (самый быстрый метод).
        Метод 5.1.4: /cises/list
        КИ передаются как параметры строки запроса values.
        """
        path = "/cises/list"
        params = {"pg": pg} if pg else {}
        for cis in cises:
            params.setdefault("values", []).append(cis)
        response = await self._request("POST", path, params=params)
        return response.json()

    async def search_cises(
        self,
        product_groups: List[str],
        gtins: Optional[List[str]] = None,
        emission_date_from: Optional[str] = None,
        emission_date_to: Optional[str] = None,
        states: Optional[List[Dict[str, Any]]] = None,
        is_aggregated: bool = False,
        per_page: int = 100,
        last_emission_date: Optional[str] = None,
        last_sgtin: Optional[str] = None,
        direction: int = 0,
    ) -> Dict[str, Any]:
        """
        Массовый поиск КИ с пагинацией.
        Метод 5.1.1: /cises/search
        """
        path = "/cises/search"
        filter_data = {
            "productGroups": product_groups,
            "isAggregated": is_aggregated
        }
        if gtins:
            filter_data["gtins"] = gtins
        if emission_date_from or emission_date_to:
            filter_data["emissionDatePeriod"] = {}
            if emission_date_from:
                filter_data["emissionDatePeriod"]["from"] = emission_date_from
            if emission_date_to:
                filter_data["emissionDatePeriod"]["to"] = emission_date_to
        if states:
            filter_data["states"] = states

        pagination = {
            "perPage": min(per_page, 1000),
            "direction": direction
        }
        if last_emission_date:
            pagination["lastEmissionDate"] = last_emission_date
        if last_sgtin:
            pagination["sgtin"] = last_sgtin

        payload = {
            "filter": filter_data,
            "pagination": pagination
        }
        response = await self._request("POST", path, json_data=payload)
        return response.json()

    async def search_all_cises(
        self,
        product_groups: List[str],
        gtins: Optional[List[str]] = None,
        emission_date_from: Optional[str] = None,
        emission_date_to: Optional[str] = None,
        states: Optional[List[Dict[str, Any]]] = None,
        is_aggregated: bool = False,
        per_page: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Автоматическая пагинация – получение всех КИ по фильтрам.
        """
        all_cises = []
        is_last_page = False
        last_emission_date = None
        last_sgtin = None

        while not is_last_page:
            result = await self.search_cises(
                product_groups=product_groups,
                gtins=gtins,
                emission_date_from=emission_date_from,
                emission_date_to=emission_date_to,
                states=states,
                is_aggregated=is_aggregated,
                per_page=per_page,
                last_emission_date=last_emission_date,
                last_sgtin=last_sgtin,
                direction=0
            )
            all_cises.extend(result.get("result", []))
            is_last_page = result.get("isLastPage", True)
            if not is_last_page and result.get("result"):
                last_item = result["result"][-1]
                last_emission_date = last_item.get("emissionDate")
                last_sgtin = last_item.get("sgtin")
            logger.info(f"Загружено {len(all_cises)} кодов")
        return all_cises

    # ---------- 2. Методы для работы с документами (заглушка) ----------
    async def create_document(
        self,
        pg: str,
        doc_type: str,
        product_document: Dict[str, Any],
        document_format: str = "MANUAL",
        second_product_document: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Создание документа в Честном знаке."""
        raise NotImplementedError("Метод create_document будет реализован позже")

# ---------- 3. Методы инвентаризации ----------
async def create_inventory_session(self, warehouse_id: str, name: str) -> dict:
    path = "/api/v3/true-api/inventory/session"  # добавили префикс
    payload = {"warehouseId": warehouse_id, "name": name}
    response = await self._request("POST", path, json_data=payload)
    return response.json()

async def add_marks_to_session(self, session_id: str, marks: List[str]) -> dict:
    path = f"/api/v3/true-api/inventory/session/{session_id}/marks"
    payload = {"marks": marks}
    response = await self._request("POST", path, json_data=payload)
    return response.json()

async def finish_inventory_session(self, session_id: str) -> dict:
    path = f"/api/v3/true-api/inventory/session/{session_id}/finish"
    response = await self._request("PUT", path)
    return response.json()

async def get_session_status(self, session_id: str) -> dict:
    path = f"/api/v3/true-api/inventory/session/{session_id}"
    response = await self._request("GET", path)
    return response.json()