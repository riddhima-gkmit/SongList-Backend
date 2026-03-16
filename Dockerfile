FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_PROJECT_ENVIRONMENT=.venv

WORKDIR /app

# System dependencies (PostgreSQL client, build tools for psycopg2, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package/dependency manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./ 

# Install Python dependencies into a local virtual environment (without dev deps)
RUN uv sync --frozen --no-dev

# Ensure the virtual environment is on PATH
ENV PATH="/app/.venv/bin:${PATH}"

# Copy the rest of the application code
COPY . .

# Expose the port used by Django / Gunicorn
EXPOSE 8000

# Default environment variables (override in deployment)
ENV DJANGO_SETTINGS_MODULE=songlist_backend.settings \
    DJANGO_DEBUG=False

# Run database migrations, collect static files, and start Gunicorn
CMD uv run python manage.py migrate --noinput && \
    uv run python manage.py collectstatic --noinput && \
    uv run gunicorn songlist_backend.wsgi:application --bind 0.0.0.0:8000 --workers=3

