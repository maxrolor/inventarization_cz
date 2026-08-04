from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.cz_api.client import CzApiClient

class MarkService:
    def __init__(self, db: AsyncSession, client_id: int):
        self.db = db
        self.client_id = client_id

    async def validate_marks_full(self, mark_codes: List[str], pg: Optional[str] = None) -> List[Dict[str, Any]]:
        """Полная проверка марок с максимальной детализацией."""
        async with CzApiClient(self.client_id, self.db) as cz:
            return await cz.get_cises_info(mark_codes, pg)

    async def validate_marks_short(self, mark_codes: List[str], pg: Optional[str] = None) -> List[Dict[str, Any]]:
        """Упрощённая проверка марок."""
        async with CzApiClient(self.client_id, self.db) as cz:
            return await cz.get_cises_short_info(mark_codes, pg)

    async def validate_marks_minimal(self, mark_codes: List[str], pg: Optional[str] = None) -> List[Dict[str, Any]]:
        """Минимальная проверка марок."""
        async with CzApiClient(self.client_id, self.db) as cz:
            return await cz.get_cises_minimal_info(mark_codes, pg)

    async def search_marks(
        self,
        product_groups: List[str],
        gtins: Optional[List[str]] = None,
        emission_date_from: Optional[str] = None,
        emission_date_to: Optional[str] = None,
        states: Optional[List[Dict[str, Any]]] = None,
        is_aggregated: bool = False,
        per_page: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Массовый поиск марок с пагинацией."""
        async with CzApiClient(self.client_id, self.db) as cz:
            return await cz.search_all_cises(
                product_groups=product_groups,
                gtins=gtins,
                emission_date_from=emission_date_from,
                emission_date_to=emission_date_to,
                states=states,
                is_aggregated=is_aggregated,
                per_page=per_page,
            )