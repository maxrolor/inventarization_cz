"""
Скрипт для получения токена на Windows с установленным КриптоПРО и pycades.
Выводит токен в консоль для копирования. (запускать на Windows)
"""

import asyncio
import logging
from cz_client import CzApiClient

logging.basicConfig(level=logging.INFO)


async def get_token():
    async with CzApiClient() as client:
        # Здесь нужно реализовать sign_data с pycades.
        # Для этого мы должны переопределить sign_data в sign_helper,
        # либо импортировать реальную функцию из другого модуля.
        # Пока предполагаем, что sign_helper содержит реальную подпись.
        token = await client.authenticate(inn="280803491835")  # ваш ИНН
        print("TOKEN:", token)
        return token


if __name__ == "__main__":
    token = asyncio.run(get_token())
    print("\n--- Скопируйте этот токен и вставьте в тесты на сервере ---")
    print(token)