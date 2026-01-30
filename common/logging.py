import os
from pathlib import Path

from django.conf import settings

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "True") == "True"


def get_logging_config():
    """
    Configure logging for the application.

    Strategy:
    - Console: JSON format for development and production
    - File: JSON format for production log aggregation
    - All application logs go to unified file
    - Django system logs go to console and file
    """
    BASE_DIR = Path(settings.BASE_DIR)
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
            "plain": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": LOG_LEVEL,
                "formatter": "json",
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(LOGS_DIR / "application.log"),
                "maxBytes": 1024 * 1024 * 10,  # 10 MB
                "backupCount": 5,
                "formatter": "json",
                "encoding": "utf-8",
                "level": "NOTSET",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["app_file", "console"],
                "level": "WARNING",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["app_file", "console"],
                "level": "ERROR",
                "propagate": False,
            },
            "django.views": {
                "handlers": ["app_file", "console"],
                "level": "WARNING",
                "propagate": False,
            },
            "django.server": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
            "request_logger": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
            "payments": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
            "users": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
            "music": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
            "tenants": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
            "common": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
            "celery": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
            "celery.beat": {
                "handlers": ["app_file", "console"],
                "level": LOG_LEVEL,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["app_file", "console"],
            "level": LOG_LEVEL,
        },
    }
