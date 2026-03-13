import os
from pathlib import Path

from django.conf import settings

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "True") == "True"

<<<<<<< Updated upstream

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
=======
    # JSON formatter for structured logs (one JSON object per line)
    formatters['json'] = {
        '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
    }
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(LOGS_DIR / "application.log"),
                "maxBytes": 1024 * 1024 * 10,  # 10 MB
                "backupCount": 5,
                "formatter": "json",
                "encoding": "utf-8",
                "level": "NOTSET",
=======
            'file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'django.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'errors.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
            'middleware_console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'json',
            },
            'middleware_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'django.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'json',
            },
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
                'filters': ['require_debug_false'],
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            "django.server": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
=======
            
            # Middleware & common (JSON format for request/response logs)
            'common.middleware': {
                'handlers': ['middleware_console', 'middleware_file'],
                'level': 'INFO',
                'propagate': False,
>>>>>>> Stashed changes
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
