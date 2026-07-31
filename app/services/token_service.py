from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client import Client
from app.core.security import encrypt_token, decrypt_token

class TokenService:
    @staticmethod
    async def get_cz_token(client_id: int, db: AsyncSession) -> str | None:
        """Возвращает расшифрованный токен для клиента."""
        client = await db.get(Client, client_id)
        if client and client.cz_token_encrypted:
            return decrypt_token(client.cz_token_encrypted)
        return None

    @staticmethod
    async def set_cz_token(client_id: int, token: str, db: AsyncSession) -> None:
        """Шифрует и сохраняет токен для клиента."""
        client = await db.get(Client, client_id)
        if not client:
            raise ValueError("Клиент не найден")
        client.cz_token_encrypted = encrypt_token(token)
        # Можно попытаться декодировать JWT и извлечь exp, но оставим пока None
        client.cz_token_expires = None
        await db.commit()

    @staticmethod
    async def has_cz_token(client_id: int, db: AsyncSession) -> bool:
        """Проверяет наличие токена у клиента."""
        client = await db.get(Client, client_id)
        return client is not None and client.cz_token_encrypted is not None