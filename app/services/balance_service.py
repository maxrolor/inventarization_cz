from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.cz_api.client import CzApiClient

class BalanceService:
    def __init__(self, db: AsyncSession, client_id: int):
        self.db = db
        self.client_id = client_id

    async def get_balance(self, warehouse_id: Optional[str] = None) -> Dict[str, Any]:
        """Получить остатки марок на складе (или всех складах)."""
        async with CzApiClient(self.client_id, self.db) as cz:
            return await cz.get_balance(warehouse_id)