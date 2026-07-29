"""
Настройка логирования через dictConfig.
Логи пишутся в файл с ротацией и дублируются в консоль.
Формат: время | уровень | имя логгера | сообщение.
"""

import logging.config
import os

# Убедимся, что папка для логов существует
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Не отключаем стандартные логгеры (например, uvicorn)

    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",  # явно указываем stdout
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 МБ
            "backupCount": 5,              # храним 5 архивных файлов
            "formatter": "default",
            "level": "DEBUG",
            "encoding": "utf-8",
        },
    },

    "root": {
        "level": "DEBUG",                 # корневой логгер пишет всё от DEBUG и выше
        "handlers": ["console", "file"],
    },

    "loggers": {
        # Для SQLAlchemy установим уровень DEBUG, чтобы видеть все SQL-запросы
        # (полезно для отладки, но в production можно изменить на WARNING)
        "sqlalchemy.engine": {
            "level": "DEBUG",
            "handlers": [],               # сообщения уходят в корневой логгер через propagate
            "propagate": True,
        },
        "sqlalchemy.pool": {
            "level": "INFO",              # информация о пуле соединений
            "handlers": [],
            "propagate": True,
        },
        # Логгеры uvicorn оставляем на уровне INFO, чтобы видеть старт/стоп
        "uvicorn": {
            "level": "INFO",
            "handlers": [],
            "propagate": True,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": [],
            "propagate": True,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": [],
            "propagate": True,
        },
    },
}


def setup_logging():
    """
    Применяет конфигурацию логирования.
    Должна вызываться один раз при старте приложения.
    """
    logging.config.dictConfig(LOGGING_CONFIG)