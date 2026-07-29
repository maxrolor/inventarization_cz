import httpx
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class INNParser:
    # Кэш для уменьшения количества запросов
    _cache = {}

    async def get_company_info(self, inn: str) -> Optional[Dict[str, Any]]:
        """Получение данных по ИНН через DaData"""
        if inn in self._cache:
            logger.info(f"Данные для ИНН {inn} взяты из кэша")
            return self._cache[inn]

        logger.info(f"Запрос данных по ИНН через DaData: {inn}")

        if not settings.dadata_api_key:
            logger.error("DADATA_API_KEY не задан в .env")
            return None

        url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
        headers = {
            "Authorization": f"Token {settings.dadata_api_key}",
            "Content-Type": "application/json"
        }
        payload = {"query": inn}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                suggestions = data.get("suggestions")
                if not suggestions:
                    logger.warning(f"По ИНН {inn} ничего не найдено")
                    return None

                party = suggestions[0]
                party_data = party.get("data", {})

                # Определяем тип (ЮЛ или ИП)
                is_legal = party_data.get("type") == "LEGAL"

                result = {
                    "name": party.get("value", ""),
                    "ceo_name": "",
                    "type": "legal" if is_legal else "individual",
                    "kpp": party_data.get("kpp") if is_legal else None,
                }

                # Извлекаем ФИО руководителя
                if is_legal:
                    management = party_data.get("management", {})
                    result["ceo_name"] = management.get("name", "")
                else:
                    fio = party_data.get("fio", {})
                    parts = [fio.get("surname", ""), fio.get("name", ""), fio.get("patronymic", "")]
                    result["ceo_name"] = " ".join(p for p in parts if p)

                # Сохраняем в кэш
                self._cache[inn] = result
                logger.info(f"Успешно получены данные для ИНН {inn}")
                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"Ошибка HTTP при запросе к DaData: {e.response.status_code}")
                return None
            except Exception as e:
                logger.error(f"Ошибка при запросе к DaData: {e}")
                return None