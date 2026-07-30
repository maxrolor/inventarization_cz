import asyncio
import logging
from cz_client import CzApiClient

logging.basicConfig(level=logging.INFO)

# Вставьте сюда токен, полученный из get_token_windows.py
MANUAL_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

async def test_with_manual_token():
    async with CzApiClient() as client:
        client.set_token(MANUAL_TOKEN)
        # Проверим, что токен работает – получим информацию по КИ
        # Это тест, что токен валиден
        try:
            cises = ["0104650117240408211dmfcZNcM4"]  # замените на реальный тестовый КИ
            info = await client.get_cises_info(cises)
            print("CIS info response:")
            print(info)
            print("Token is valid!")
        except Exception as e:
            print(f"Error: {e}")

async def test_authenticate():
    # Этот тест требует реальной подписи – работает только на Windows
    async with CzApiClient() as client:
        try:
            token = await client.authenticate(inn="280803491835")
            print(f"Authenticated, token: {token[:50]}...")
        except Exception as e:
            print(f"Authentication failed (expected on server without CryptoPro): {e}")

if __name__ == "__main__":
    # Сначала тест с ручным токеном (работает везде)
    asyncio.run(test_with_manual_token())
    # Затем попытка аутентификации (заработает только на Windows с pycades)
    asyncio.run(test_authenticate())