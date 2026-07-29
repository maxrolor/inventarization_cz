import logging
from celery import shared_task
from app.celery_tasks.utils import get_sync_db
from app.models.inventory import InventorySession, ScannedMark, InventoryDifference
from app.models.client import Client
from app.services.cz_api.client import CzApiClient
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="inventory.compare_with_cz")
def compare_with_cz(self, session_id: int, client_id: int):
    """
    Фоновая задача для сравнения сканированных марок с остатками ЧЗ.
    """
    logger.info(f"Запуск сравнения для сессии {session_id}, клиент {client_id}")

    with next(get_sync_db()) as db:  # получаем синхронную сессию
        # 1. Получаем сессию и клиента
        session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
        if not session:
            raise ValueError(f"Сессия {session_id} не найдена")
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client or not client.cz_token:
            raise ValueError(f"Клиент {client_id} не имеет токена ЧЗ")

        # 2. Получаем все сканированные марки
        scanned_marks = db.query(ScannedMark).filter(ScannedMark.session_id == session_id).all()
        mark_codes = [m.mark_code for m in scanned_marks]

        # 3. Получаем остатки из ЧЗ через клиент
        cz_client = CzApiClient(client)
        try:
            balances = cz_client.get_balances()  # предполагаем, что возвращает список марок с остатками
        except Exception as e:
            logger.error(f"Ошибка при получении остатков: {e}")
            self.update_state(state="FAILURE", meta={"error": str(e)})
            raise

        # 4. Сравниваем и создаём расхождения
        # Здесь логика сравнения (упрощённо)
        # ...

        # 5. Сохраняем расхождения в БД
        # ... (создание объектов InventoryDifference)

        # 6. Обновляем статус сессии
        session.total_mismatches = len(differences)  # пример
        db.commit()

    return {"status": "completed", "session_id": session_id, "mismatches": 0}  # вернуть результат


@shared_task(name="inventory.sync_balances")
def sync_balances():
    """
    Периодическая синхронизация остатков для всех клиентов,
    у которых настроен токен ЧЗ.
    """
    from app.models.client import Client
    from app.services.cz_api.client import CzApiClient
    from app.celery_tasks.utils import get_sync_db

    logger.info("Запуск синхронизации остатков")
    with next(get_sync_db()) as db:
        clients = db.query(Client).filter(Client.cz_token.isnot(None)).all()
        for client in clients:
            try:
                cz = CzApiClient(client)
                balances = cz.get_balances()
                # Здесь логика сохранения остатков в кэш или временную таблицу
                # Можно сохранять в Redis, например, чтобы быстро получать при сравнении
                logger.info(f"Синхронизация для клиента {client.id} успешна")
            except Exception as e:
                logger.error(f"Ошибка синхронизации клиента {client.id}: {e}")
    return {"status": "completed", "clients_processed": len(clients)}


@shared_task(name="inventory.check_write_off_statuses")
def check_write_off_statuses():
    """
    Проверка статусов отправленных документов списания (если документ ещё в статусе pending)
    """
    from app.models.inventory import WriteOffDocument
    from app.services.cz_api.client import CzApiClient
    from app.celery_tasks.utils import get_sync_db

    with next(get_sync_db()) as db:
        pending_docs = db.query(WriteOffDocument).filter(WriteOffDocument.status == "pending").all()
        for doc in pending_docs:
            # Получить клиента
            client = doc.session.client
            if not client.cz_token:
                continue
            cz = CzApiClient(client)
            try:
                status_info = cz.get_document_status(doc.document_id)
                # Обновить статус документа в БД
                doc.status = status_info.get("status", "error")
                doc.sent_at = status_info.get("updated_at") if doc.sent_at is None else doc.sent_at
                db.commit()
                logger.info(f"Документ {doc.id} обновлён: {doc.status}")
            except Exception as e:
                logger.error(f"Ошибка проверки документа {doc.id}: {e}")
    return {"status": "completed", "docs_checked": len(pending_docs)}