from .base import *
import os

# Allowed hosts for development
ALLOWED_HOSTS = os.getenv("DEV_ALLOWED_HOSTS", "").split(",")

DEBUG = os.getenv("DEV_DEBUG", "1") == "1"

# Development database (PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DEV_DB_NAME"),
        "USER": os.getenv("DEV_DB_USER"),
        "PASSWORD": os.getenv("DEV_DB_PASSWORD"),
        "HOST": os.getenv("DEV_DB_HOST"),
        "PORT": os.getenv("DEV_DB_PORT"),
    }
}

 