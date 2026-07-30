import asyncio
import base64
import json
import logging
from typing import Optional, List, Dict, Any
import httpx

# Импорт заглушки подписи – она не используется, если мы передаём токен вручную
from .sign_helper import sign_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CzApiClient:
    """
    Асинхронный клиент для True API Честного знака (песочница).
    Поддерживает ручную установку токена (для тестирования на сервере без подписи).
    """

    def __init__(
        self,
        base_url: str = "https://markirovka.sandbox.crptech.ru/api/v3/true-api",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.base_url = base_url
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

    def set_token(self, token: str):
        """Установить токен вручную (для использования без аутентификации)."""
        self._token = token
        logger.info("Token set manually")

    # ---------- Аутентификация (использует подпись – работает только на Windows) ----------

    async def _get_auth_key(self) -> Dict[str, str]:
        url = f"{self.base_url}/auth/key"
        response = await self._http_client.get(url)
        response.raise_for_status()
        return response.json()

    async def authenticate(
        self,
        inn: Optional[str] = None,
        united_token: bool = False,
    ) -> str:
        """Получение токена с подписью (требует реализации sign_data с pycades)."""
        auth_data = await self._get_auth_key()
        uuid = auth_data["uuid"]
        data = auth_data["data"]

        signed_data = sign_data(data)  # должна быть реальная подпись

        url = f"{self.base_url}/auth/simpleSignIn"
        payload = {
            "uuid": uuid,
            "data": signed_data,
            "unitedToken": united_token,
        }
        if inn:
            payload["inn"] = inn

        response = await self._http_client.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        token = result.get("token")
        if not token:
            raise RuntimeError("Token not received")
        self._token = token
        logger.info("Authentication successful")
        return token

    # ---------- Общий метод запроса с авторизацией ----------

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        if not self._token:
            raise RuntimeError("Not authenticated. Call authenticate() or set_token() first.")

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
                    logger.warning("Token expired, re-authenticating...")
                    # Здесь можно вызвать повторную аутентификацию, но для теста просто пробрасываем.
                    response.raise_for_status()
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 500, 502, 503):
                    wait = 2 ** attempt
                    logger.warning(f"Retry {attempt+1}/{self.max_retries} after {wait}s")
                    await asyncio.sleep(wait)
                    continue
                raise
        raise RuntimeError("Max retries exceeded")

    # ---------- Методы API ----------

    async def get_cises_info(self, cises: List[str]) -> Dict[str, Any]:
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
        # Кодируем product_document в base64
        product_doc_json = json.dumps(product_document, ensure_ascii=False)
        product_doc_b64 = base64.b64encode(product_doc_json.encode("utf-8")).decode("utf-8")

        # Подписываем исходный JSON (откреплённая подпись) – на сервере это заглушка,
        # но если мы используем ручной токен, то подпись не проверяется? Нет, для создания документа
        # нужна откреплённая подпись документа, она проверяется отдельно.
        # Поэтому этот метод тоже будет требовать реальной подписи.
        # Пока оставляем заглушку, но для реального использования нужна подпись.
        signature = sign_data(product_doc_json)

        payload = {
            "document_format": document_format,
            "product_document": product_doc_b64,
            "type": doc_type,
            "signature": signature,
        }

        if second_product_document:
            second_json = json.dumps(second_product_document, ensure_ascii=False)
            second_b64 = base64.b64encode(second_json.encode("utf-8")).decode("utf-8")
            second_sig = sign_data(second_json)
            payload["second_product_document"] = second_b64
            payload["second_signature"] = second_sig

        path = "/lk/documents/create"
        params = {"pg": pg}
        response = await self._request("POST", path, params=params, json_data=payload)
        result = response.json()
        doc_id = result.get("id")
        if not doc_id:
            raise RuntimeError(f"Document creation failed: {result}")
        return doc_id

    # ---------- Удобные обёртки ----------

    async def create_cis_notice(
        self,
        pg: str,
        participant_inn: str,
        action_date: str,
        action: str,
        codes: List[str],
        **kwargs,
    ) -> str:
        body = {
            "participantInn": participant_inn,
            "actionDate": action_date,
            "action": action,
            "codes": [{"code": c} for c in codes],
        }
        body.update(kwargs)
        return await self.create_document(pg, "CIS_NOTICE", body)

    async def create_report_reweighing(
        self,
        pg: str,
        participant_inn: str,
        codes: List[Dict[str, Any]],
    ) -> str:
        body = {
            "participantInn": participant_inn,
            "codes": codes,
        }
        return await self.create_document(pg, "REPORT_REWEIGHING", body)

    async def create_write_off(
        self,
        pg: str,
        participant_id: str,
        dropout_reason: str,
        sntins: List[str],
        source_doc_type: str,
        source_doc_date: str,
        source_doc_num: str,
        source_doc_name: Optional[str] = None,
        with_child: bool = True,
        **kwargs,
    ) -> str:
        body = {
            "participantId": participant_id,
            "dropoutReason": dropout_reason,
            "withChild": with_child,
            "sntins": sntins,
            "sourceDocType": source_doc_type,
            "sourceDocDate": source_doc_date,
            "sourceDocNum": source_doc_num,
        }
        if source_doc_name:
            body["sourceDocName"] = source_doc_name
        body.update(kwargs)
        return await self.create_document(pg, "WRITE_OFF", body)