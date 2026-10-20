# Sonderring v0 (Django & SQL Architecture)

Sonderring is a collaborative trip-planning web application designed for groups to manage stays, transportation (navs), and activities (dos) while maintaining top-tier cybersecurity standards for confirmation codes and sensitive travel data.

## Tech Stack
- **Backend**: Python / Django (Server-rendered templates + Django REST Framework API for mobile clients)
- **Database**: PostgreSQL (Relational schema with hybrid time granularity and strict row-level security)
- **Security**: AES-256-GCM application-level field encryption for booking confirmation codes.

## Quickstart & Startup Instructions

### 1. Prerequisites
- Python 3.9+
- PostgreSQL (or local SQLite for development)
- Virtual environment tool (`venv`)

### 2. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
You can set the following environment variables:
- `DJANGO_SECRET_KEY`: Secret key for Django cryptographic signing.
- `DJANGO_DEBUG`: Set to `True` for development, `False` for production.
- `FIELD_ENCRYPTION_KEY`: Base64-encoded 32-byte key for AES-256-GCM field encryption.
- `DATABASE_URL`: PostgreSQL connection URL (e.g., `postgresql://user:password@localhost:5432/sonderring`).

### 4. Database Setup & Migrations
To initialize the database schema:
```bash
# If using direct PostgreSQL schema:
psql -d sonderring -f db/schema.sql

# Or using Django ORM migrations:
python manage.py makemigrations core
python manage.py migrate
```

### 5. Run Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.
