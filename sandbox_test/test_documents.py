import asyncio
import logging
from cz_client import CzApiClient

logging.basicConfig(level=logging.INFO)

MANUAL_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # вставьте ваш токен

async def test_create_cis_notice():
    async with CzApiClient() as client:
        client.set_token(MANUAL_TOKEN)
        doc_id = await client.create_cis_notice(
            pg="milk",
            participant_inn="280803491835",
            action_date="2026-07-30",
            action="LOST_INVENTORY",
            codes=["0104650117240408211dmfcZNcM4"]  # замените на реальный КИ
        )
        print(f"CIS_NOTICE created with ID: {doc_id}")

async def test_cises_info():
    async with CzApiClient() as client:
        client.set_token(MANUAL_TOKEN)
        info = await client.get_cises_info(["0104650117240408211dmfcZNcM4"])
        print("CIS info response:")
        print(info)

if __name__ == "__main__":
    asyncio.run(test_cises_info())
    # asyncio.run(test_create_cis_notice())  # раскомментируйте для отправки документа