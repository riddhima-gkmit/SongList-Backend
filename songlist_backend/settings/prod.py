from .base import *
import os

# Allowed hosts for production
ALLOWED_HOSTS = os.getenv("PROD_ALLOWED_HOSTS", "").split(",")

DEBUG = os.getenv("PROD_DEBUG", "1")  == "1"

# Production database (PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("PROD_DB_NAME"),
        "USER": os.getenv("PROD_DB_USER"),
        "PASSWORD": os.getenv("PROD_DB_PASSWORD"),
        "HOST": os.getenv("PROD_DB_HOST"),
        "PORT": os.getenv("PROD_DB_PORT"),
    }
}

