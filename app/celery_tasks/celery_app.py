from celery import Celery
from .config import CeleryConfig

celery_app = Celery("inventarization_cz")
celery_app.config_from_object(CeleryConfig)

# Автоматическое обнаружение задач в модулях с именем *_tasks.py
celery_app.autodiscover_tasks(["app.celery_tasks"])

# Для удобства можно добавить обработку сигналов (например, для создания сессии БД)