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
* **Strict Validation**: Regex-based validation for emails, names, and phone numbers

---

### User Management

*   **Self-Service**: Users manage their own profile (`/users/me`)
*   **Admin Control**: Admins manage all users (`/users`)
*   **Safety**: Admins **cannot delete their own account** (must be deleted by another admin)

---

### Song Management

*   **Submission**: Users submit songs for review (`PENDING`)
*   **Moderation**: Admins approve or reject songs
*   **Lifecycle**: `PENDING` → `APPROVED` / `REJECTED`
*   **Protection**: Approved songs cannot be edited without re-approval
*   **Filtering**: Filter by artist, genre, and album

---

### Playlist Management

*   **Personalized**: Users create and manage their own playlists
*   **Curated Content**: Only `APPROVED` songs can be added
*   **Admin Access**: Admins can view/delete playlists but **cannot modify** them (create/update/add songs)

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
├── uv.lock                 # Locked dependency versions

├── songlist_backend/       # Project settings & configuration
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── dev.py          # Development settings
│   │   └── prod.py         # Production settings
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py

├── common/                 # Shared utilities
│   ├── management/         # Management commands
│   │   └── commands/
│   │       ├── seed_genres.py # Seed initial genres
│   │       ├── seed_users.py  # Seed regular users
│   │       └── seed_admins.py # Seed admin users
│   ├── models.py           # Abstract base models
│   ├── permissions.py      # Custom permissions (RBAC)
│   ├── pagination.py       # Standard pagination
│   ├── constants.py        # Global constants
│   └── enums.py            # Global enums

├── users/                  # Authentication & user management
│   ├── models.py           # User model
│   ├── serializers/
│   │   ├── auth.py         # Login/Register serializers
│   │   └── user.py         # User profile serializers
│   ├── views/
│   │   ├── auth.py         # Auth views
│   │   └── user.py         # User views
│   └── urls.py

├── music/                  # Songs & playlists
│   ├── models/             # Application models
│   │   ├── genre.py
│   │   ├── song.py
│   │   ├── playlist.py
│   │   └── playlist_song.py
│   ├── serializers/        # Resource serializers
│   │   ├── song.py
│   │   ├── playlist.py
│   │   └── review.py
│   ├── views/              # Resource views
│   │   ├── song.py
│   │   ├── playlist.py
│   │   └── review.py
│   └── urls.py
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

### 6. Data Seeding (Optional)

You can populate the database with initial data using the following commands:

**Seed Genres** (must run first):
```bash
python manage.py seed_genres
```

**Seed Users** (creates 5 regular users):
```bash
python manage.py seed_users
```

**Seed Admins** (creates 5 admin users):
```bash
python manage.py seed_admins
```

---

### 7. Start Development Server

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

### Postman Collection

A complete Postman collection (`SongList.postman_collection.json`) is included in the root directory for testing all API endpoints.

---
