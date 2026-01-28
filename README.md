# SongList Backend

Multi-tenant music content management REST API built with **Django** and **Django REST Framework**. Organizations (tenants) manage users, song catalogs, playlists, song requests, and premium subscriptions with strict isolation and role-based access.

---

## Features

- **Multi-tenancy:** Tenant isolation; URL-based tenant context for auth (`/tenant/<tenant_id>/auth/...`).
- **Roles:** LISTENER (self-serve, playlists, song requests), ADMIN (tenant users, content, payments), SUPER_ADMIN (tenants, GLOBAL songs, genres, platform metrics).
- **Auth:** OTP-based login and email verification; JWT access/refresh tokens; token blacklist and denylist; password reset.
- **Songs:** GLOBAL (platform) vs TENANT (per-tenant) visibility; tenant-song links; filters (title, artist, genre, album).
- **Playlists:** User-owned; LISTENER own only, ADMIN full CRUD in tenant; only approved tenant songs.
- **Song requests:** Users request → admins approve/reject/fulfill (link or create song).
- **Payments:** Razorpay payment links, webhooks, subscription status; per-tenant premium.

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Backend | Django, Django REST Framework |
| Auth | SimpleJWT, pyotp, Redis (OTP cache, token denylist) |
| Database | PostgreSQL |
| Cache / broker | Redis (django-redis, Celery) |
| Payments | Razorpay |
| Tasks | Celery, Celery Beat |
| Tooling | uv, python-dotenv |

**Python:** 3.13+

---

## Prerequisites

- Python 3.13+
- PostgreSQL
- Redis (cache, Celery broker)
- Razorpay account (sandbox for dev)

---

## Quick Start

1. **Clone and install**
   ```bash
   git clone https://github.com/riddhima-gkmit/SongList-Backend.git
   cd SongList-Backend
   uv sync
   ```

2. **Environment**
   - Copy `.env.example` to `.env`.
   - Set at least: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `REDIS_URL`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`.
   - For local dev: `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`.

3. **Database**
   ```bash
   uv run python manage.py migrate
   ```

4. **Superuser (SUPER_ADMIN)**
   ```bash
   uv run python manage.py createsuperuser
   ```
   Use email as identifier. No tenant.

5. **Default tenant** (Django shell)
   ```bash
   uv run python manage.py shell
   ```
   ```python
   from tenants.models import Tenant
   t = Tenant.objects.create(name="Default Tenant", is_active=True)
   print(t.id)  # use for tenant-scoped auth URLs
   ```

6. **Run server**
   ```bash
   uv run python manage.py runserver
   ```
   API base: `http://localhost:8000/api/v1/`

7. **(Optional) Celery**
   ```bash
   celery -A songlist_backend worker -l info
   celery -A songlist_backend beat -l info
   ```

---

## Seeding

| Command | Purpose |
|---------|---------|
| `uv run python manage.py seed_genres` | Seed genres (run first) |
| `uv run python manage.py seed_tenants` | Seed tenants |
| `uv run python manage.py seed_songs` | Seed songs (requires superuser + genres) |

---

## Project Structure

```
SongList-Backend/
├── manage.py
├── pyproject.toml, uv.lock
├── songlist_backend/     # settings, urls, celery
├── common/               # base models, permissions, pagination, logging, middleware, seed commands
├── users/                # auth, user management, filters
├── tenants/              # tenant CRUD (SUPER_ADMIN)
├── music/                # genres, songs, tenant_songs, playlists, song_requests, filters
├── payments/             # Razorpay links, webhooks, subscription status
└── .env.example
```

---

## API Overview

Base URL: **`/api/v1`**. JWT Bearer auth for protected routes.

| Group | Examples |
|-------|----------|
| **Auth** | `POST /tenant/<tenant_id>/auth/register/`, `.../login/`, `.../verify-email/`, `.../password-reset/`; `POST /auth/logout/`, `POST /auth/super-admin/login/` (+ verify-otp); `POST /token/refresh/` |
| **Users** | `GET|PATCH|DELETE /users/me/`, `POST /users/me/change-password/`; `GET|POST /users/`, `GET|PATCH|DELETE /users/<id>/`, `GET /users/deleted/`, `POST /users/<id>/restore/` |
| **Tenants** | `GET|POST /tenants/`, `GET|PATCH|DELETE /tenants/<id>/`, `PATCH .../activate/`, `.../deactivate/` |
| **Admins** | `GET /super-admin/admins/` |
| **Songs** | `GET|POST /songs/`, `GET|PATCH|DELETE /songs/<id>/`, `POST /songs/bulk-add/` |
| **Tenant songs** | `GET|POST /tenant/songs/`, `GET|DELETE /tenant/songs/<id>/`, `POST /tenant/songs/bulk-delete/` |
| **Playlists** | `GET|POST /playlists/`, `GET|PATCH|DELETE /playlists/<id>/`, `GET|POST|DELETE /playlists/<id>/songs/` |
| **Song requests** | `GET|POST /song-requests/`, `GET|PATCH|DELETE /song-requests/<id>/`, `POST .../review/`, `.../fulfill/` |
| **Genres** | `GET|POST /genres/`, `GET|PATCH|DELETE /genres/<id>/` |
| **Payments** | `POST /payments/create-payment-link/`, `GET /payments/subscription/`, `POST /payments/webhook/razorpay/`; `GET /payments/super-admin/subscriptions/`, `.../payments/` |

List endpoints support `page`, `page_size`. Many support extra query filters (e.g. `is_active`, `name`, `email` for users/admins; `title`, `artist`, `genre`, `album` for songs).

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `1` / `0` |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL |
| `REDIS_URL` | Redis URL |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Razorpay |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, etc. | SMTP / console |
| `FRONTEND_URL` | Frontend base URL (e.g. email links) |

See `.env.example` for a full template.

---

## Documentation

- **Full Documentation:** [Songlist SaaS Documentation](https://riddhima-gkmit.github.io/Songlist-Multitenant-Documentation/functional-docs/).


---


