# SongList – Backend (Django REST API)

SongList is a **music content management platform** that allows users to submit songs, organize them into playlists, and enables admins to moderate and manage content.
This repository contains the **backend REST API**, built using **Django REST Framework**, providing secure authentication, role-based access control, song moderation workflows, and playlist management.

---

## Features

### Authentication & Authorization

* Secure JWT authentication using **SimpleJWT**
* Access & refresh token support
* Role-based access control (User / Admin)
* Unique email-based user accounts
* Object-level permissions (Owner or Admin)

---

### Song Management

* Submit songs for admin approval
* Song lifecycle management (`PENDING`, `APPROVED`, `REJECTED`)
* Update song details (approval required)
* Soft delete support
* Advanced filtering (artist, genre, album)

---

### Playlist Management

* Create and manage user playlists
* Add and remove approved songs
* Prevent duplicate songs in playlists
* Soft delete playlists

---

### Admin Panel APIs

* Manage users
* Approve or reject songs
* Access all songs and playlists
* System-level overview endpoints

---

## Tech Stack

| Category              | Technology            |
| --------------------- | --------------------- |
| Backend               | Django REST Framework |
| Authentication        | SimpleJWT             |
| Database              | PostgreSQL            |
| Dependency Management | uv                    |
| Environment           | Python 3.12+          |
| API Style             | RESTful JSON APIs     |

---

## Project Structure

```

songlist/
├── manage.py
├── .env
├── .gitignore
├── README.md

├── pyproject.toml          # uv / project metadata & dependencies
├── uv.lock                 # Locked dependency versions (auto-generated)

├── .venv/                  # Virtual environment created by uv (local only)
│   ├── bin/
│   ├── lib/
│   └── pyvenv.cfg

├── config/                     # Project-level configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py              # Shared settings
│       ├── dev.py               # Development settings
│       └── prod.py              # Production settings

├── common/                      # Shared utilities (optional but clean)
│   ├── __init__.py
│   ├── permissions.py           # Custom permissions
│   ├── pagination.py
│   ├── responses.py             # Standard API responses
│   └── enums.py                 # Global enums (roles, status)

├── users/                       # Authentication & user management
│   ├── __init__.py
│   ├── admin.py                 # Admin panel unused (optional)
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py
│   ├── enums.py                 # UserRole enum
│   └── constants.py

├── music/                       # Songs & playlists
│   ├── __init__.py
│   ├── apps.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── genre.py
│   │   ├── song.py
│   │   ├── playlist.py
│   │   └── playlist_song.py
│   ├── serializers/
│   │   ├── __init__.py
│   │   ├── genre.py
│   │   ├── song.py
│   │   └── playlist.py
│   ├── views/
│   │   ├── __init__.py
│   │   ├── song.py
│   │   ├── playlist.py
│   │   └── review.py            # Admin approve/reject logic
│   ├── urls.py
│   ├── permissions.py
│   ├── enums.py                 # SongStatus enum
│   └── constants.py


```

---

## Setup & Installation

### 1. Clone the Repository

```bash
git clone git@github.com:riddhima-gkmit/SongList-Backend.git
cd songlist-backend
```

---

### 2. Create and Activate Virtual Environment (uv)

```bash
uv venv
uv sync
```

---

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/songlist
```

---

### 4. Run Database Migrations

```bash
python manage.py migrate
```

---

### 5. Create Admin User

```bash
python manage.py createsuperuser
```

---

### 6. Start Development Server

```bash
python manage.py runserver
```

API is now available at:

```
http://localhost:8000/api/v1/
```

---

## API Overview

### Authentication APIs

* Register
* Login
* Token refresh
* Change password
* Logout

---

### User APIs

* Self-service profile management (`/users/me`)
* Admin user management (`/users`)

---

### Song APIs

* Submit songs
* List songs (user → own, admin → all)
* Retrieve, update, and delete songs
* Admin approval workflow

---

### Playlist APIs

* Create and manage playlists
* Add or remove songs

---

## Documentation

Full documentation is available at:
https://riddhima-gkmit.github.io/SongList-Documentation/

---


