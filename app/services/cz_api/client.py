"""
Заглушка для клиента Честного знака.
"""

class CzApiClient:
    """Клиент для работы с True API Честного знака (заглушка)."""
    
    def __init__(self, client):
        self.client = client
        self.base_url = "https://markirovka.sandbox.crptech.ru"

    def get_balances(self):
        return []

    def verify_marks(self, mark_codes):
        return [{"code": code, "status": "valid"} for code in mark_codes]

    def create_write_off_document(self, marks):
        return {"document_id": "test_doc_123", "status": "pending"}

    def get_document_status(self, document_id):
        return {"status": "completed", "updated_at": "2026-07-29T12:00:00"}
