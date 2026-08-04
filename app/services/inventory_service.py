import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.inventory import (
    InventorySession, InventorySessionStatus,
    ScannedMark, InventoryDifference, DifferenceType
)
from app.services.cz_api.client import CzApiClient

logger = logging.getLogger(__name__)

class InventoryService:
    def __init__(self, db: AsyncSession, client_id: int):
        self.db = db
        self.client_id = client_id

    async def create_session(self, warehouse_id: str, name: Optional[str] = None) -> InventorySession:
        """
        Создать новую сессию инвентаризации:
        - сначала в Честном знаке (получить session_id),
        - затем сохранить в локальной БД.
        """
        async with CzApiClient(self.client_id, self.db) as cz:
            cz_data = await cz.create_inventory_session(warehouse_id, name or "Инвентаризация")

        session = InventorySession(
            client_id=self.client_id,
            status=InventorySessionStatus.ACTIVE,
            started_at=datetime.utcnow(),
            extra_data={
                "cz_session_id": cz_data.get("id"),  # сохраняем ID из ЧЗ
                "cz_response": cz_data
            }
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_sessions(self, status: Optional[InventorySessionStatus] = None) -> List[InventorySession]:
        """Получить список сессий клиента, опционально фильтруя по статусу."""
        query = select(InventorySession).where(InventorySession.client_id == self.client_id)
        if status:
            query = query.where(InventorySession.status == status)
        result = await self.db.execute(query.order_by(InventorySession.started_at.desc()))
        return result.scalars().all()

    async def get_session(self, session_id: int) -> Optional[InventorySession]:
        """Получить одну сессию по ID (с проверкой принадлежности клиенту)."""
        result = await self.db.execute(
            select(InventorySession).where(
                InventorySession.id == session_id,
                InventorySession.client_id == self.client_id
            )
        )
        return result.scalar_one_or_none()

    async def add_scanned_marks(self, session_id: int, mark_codes: List[str]) -> dict:
        """
        Добавить отсканированные марки в сессию.
        - Проверяем сессию (активна, принадлежит клиенту)
        - Отправляем марки в ЧЗ через API
        - Сохраняем марки локально в ScannedMark
        - Возвращаем результат от ЧЗ (если нужно)
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Сессия не найдена")
        if session.status != InventorySessionStatus.ACTIVE:
            raise ValueError("Сессия не активна (завершена или отменена)")

        # Получаем cz_session_id из extra_data
        cz_session_id = session.extra_data.get("cz_session_id") if session.extra_data else None
        if not cz_session_id:
            raise ValueError("Не найден ID сессии в Честном знаке")

        # Отправляем в ЧЗ
        async with CzApiClient(self.client_id, self.db) as cz:
            cz_result = await cz.add_marks_to_session(cz_session_id, mark_codes)

        # Сохраняем марки локально
        for code in mark_codes:
            mark = ScannedMark(
                session_id=session.id,
                mark_code=code,
                is_valid=True  # пока считаем валидными, проверка может быть позже
            )
            self.db.add(mark)

        # Обновляем счётчик сканированных марок
        session.total_scanned += len(mark_codes)
        await self.db.commit()
        return cz_result

    async def finish_session(self, session_id: int) -> dict:
        """
        Завершить инвентаризацию:
        - вызвать API завершения в ЧЗ,
        - обновить статус локально.
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Сессия не найдена")
        if session.status != InventorySessionStatus.ACTIVE:
            raise ValueError("Сессия уже завершена или отменена")

        cz_session_id = session.extra_data.get("cz_session_id") if session.extra_data else None
        if not cz_session_id:
            raise ValueError("Не найден ID сессии в Честном знаке")

        async with CzApiClient(self.client_id, self.db) as cz:
            cz_result = await cz.finish_inventory_session(cz_session_id)

        session.status = InventorySessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        session.extra_data = session.extra_data or {}
        session.extra_data["finish_response"] = cz_result
        await self.db.commit()
        return cz_result

    async def cancel_session(self, session_id: int) -> None:
        """Отменить сессию (без вызова ЧЗ, просто локально)."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Сессия не найдена")
        if session.status != InventorySessionStatus.ACTIVE:
            raise ValueError("Сессия уже завершена")
        session.status = InventorySessionStatus.CANCELLED
        await self.db.commit()