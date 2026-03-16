from .base import *
import os

# Allowed hosts for development
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Development database (SQLite)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

