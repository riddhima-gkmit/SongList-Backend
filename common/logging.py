"""
Centralized logging configuration for the SongList application.

Provides structured logging with:
- Console and file handlers
- Rotating file logs
- Environment-based configuration
- Application-specific loggers
"""
import os
from pathlib import Path


def get_logging_config(base_dir):
    """
    Get logging configuration dictionary.
    
    Args:
        base_dir: Base directory path for log files
        
    Returns:
        dict: Logging configuration for Django LOGGING setting
    """
    # Ensure logs directory exists
    log_dir = Path(base_dir) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Determine log level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Determine formatters
    formatters = {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    }

    # Add JSON formatter if library is available
    try:
        import pythonjsonlogger
        formatters['json'] = {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        }
    except ImportError:
        # Fallback to verbose if json logger is not available
        pass

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
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
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
                'filters': ['require_debug_false'],
            },
        },
        'loggers': {
            # Django core loggers
            'django': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console', 'file', 'error_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.security': {
                'handlers': ['console', 'error_file'],
                'level': 'WARNING',
                'propagate': False,
            },
            
            # Middleware & common
            'common.middleware': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            
            # Application loggers
            'users': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'music': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'payments': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'tenants': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            
            # Background tasks
            'celery': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'tasks': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            
            # Email logging
            'email': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console', 'file', 'error_file'],
            'level': log_level,
        },
    }
