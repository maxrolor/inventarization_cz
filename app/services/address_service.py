import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)

_cache = {}
CACHE_TTL_SECONDS = 600  # 10 минут

async def suggest_addresses(query: str, count: int = 20) -> List[Dict[str, Any]]:
    """
    Получение подсказок по адресам через DaData с кэшированием.
    Поиск выполняется до уровня дома (включая номера домов).
    """
    if not settings.dadata_api_key:
        logger.warning("DADATA_API_KEY не задан")
        return []

    if not query or len(query) < 2:
        return []

    cache_key = f"{query}|{count}"
    now = datetime.now()

    if cache_key in _cache:
        timestamp, cached_result = _cache[cache_key]
        if now - timestamp < timedelta(seconds=CACHE_TTL_SECONDS):
            logger.debug(f"Возвращены данные из кэша для '{query}'")
            return cached_result
        else:
            del _cache[cache_key]

    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
    headers = {
        "Authorization": f"Token {settings.dadata_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "count": count,
        "from_bound": {"value": "city"},
        "to_bound": {"value": "house"},  # ищем до дома (включая номер)
        "locations": [{"country": "*"}]  # не ограничиваем страну
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            suggestions = data.get("suggestions", [])
            results = [
                {
                    "value": s.get("value", ""),
                    "data": s.get("data", {})
                }
                for s in suggestions
            ]
            _cache[cache_key] = (now, results)
            logger.debug(f"Получено {len(results)} подсказок для '{query}' (сохранено в кэш)")
            return results
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка HTTP при запросе адресов: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при запросе адресов: {e}")
            return []


def clear_address_cache():
    global _cache
    _cache.clear()
    logger.info("Кэш адресов очищен")