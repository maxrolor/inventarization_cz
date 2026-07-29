import re

def validate_inn(inn: str) -> bool:
    # простая проверка длины
    return len(inn) in (10, 12) and inn.isdigit()
