from celery.schedules import crontab

# Расписание периодических задач
beat_schedule = {
    # Задача синхронизации остатков (каждый день в 3:00 утра)
    "sync_balances_every_day": {
        "task": "inventory.sync_balances",  # имя задачи
        "schedule": crontab(hour=3, minute=0),
        "args": (),
        "options": {
            "expires": 3600,  # задача устаревает через час, если не выполнена
        },
    },
    # Можно добавить другие задачи, например, проверку статусов документов каждые 15 минут
    "check_document_statuses": {
        "task": "inventory.check_write_off_statuses",
        "schedule": crontab(minute="*/15"),
        "args": (),
    },
}