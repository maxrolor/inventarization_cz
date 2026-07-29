from app.models.client import Client, CzEnvironment

def get_cz_api_url(client: Client) -> str:
    """Возвращает URL API Честного ЗНАКа для указанного клиента"""
    if client.cz_api_url:
        return client.cz_api_url
    if client.cz_environment == CzEnvironment.SANDBOX:
        return "https://markirovka.sandbox.crptech.ru"
    return "https://cdn.crpt.ru/api/v4/true-api/"