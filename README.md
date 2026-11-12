# Sonderring

Sonderring is a collaborative trip-planning canvas designed for groups to plan and manage journeys across four foundational dimensions—**Move**, **Stay**, **Taste**, and **Play**—while maintaining top-tier cybersecurity standards for confirmation codes and sensitive travel credentials.

---

## 📚 Foundational Documentation Catalog

The repository includes a comprehensive, programming language–agnostic documentation suite designed so that any engineering team can understand, architect, and build Sonderring from scratch:

| Document | Purpose | File Link |
| :--- | :--- | :--- |
| **Domain Nomenclature** | Official definitions for TripSpaces, Dimensions, Items, Categories, and Inputs vs. Attributes. | [`AGENTS.md`](AGENTS.md) |
| **Product Requirements (PRD)** | Vision, personas, functional requirements, and non-functional requirements. | [`docs/PRD.md`](docs/PRD.md) |
| **MVP Scope & Roadmap** | Strict Phase 1 (MVP in-scope) boundaries vs. Phase 2 and Phase 3 roadmaps. | [`docs/MVP.md`](docs/MVP.md) |
| **Cybersecurity Architecture** | Application-level AES-256-GCM envelope encryption, Document Vault, RBAC, and STRIDE threat model. | [`docs/CYBERSECURITY.md`](docs/CYBERSECURITY.md) |
| **Site Architecture & Flows** | Sitemap, screen inventory, status-first modal flows, and responsive breakpoints. | [`docs/PAGE_OUTLINE.md`](docs/PAGE_OUTLINE.md) |
| **Canonical Data Model** | Entity-relationship diagrams, attribute definitions, state machines, and constraints. | [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) |
| **API Contract Specification** | RESTful HTTP/JSON endpoints, request/response payloads, and error envelopes. | [`docs/API_SPECIFICATION.md`](docs/API_SPECIFICATION.md) |
| **Markdown Sync Specification** | Canonical grammar, section ordering, and bidirectional sync protocols with `docs/seed-trips/`. | [`docs/MARKDOWN_SYNC_SPEC.md`](docs/MARKDOWN_SYNC_SPEC.md) |
| **Living User Stories & AC** | Active user stories and testable acceptance criteria synchronized with specifications. | [`docs/livingUserStoriesAndAcceptanceCriteria.md`](docs/livingUserStoriesAndAcceptanceCriteria.md) |
| **Item Attributes Reference** | Field and form input guidelines across all four dimensions. | [`docs/tripItemAttributesReference.md`](docs/tripItemAttributesReference.md) |
| **Tasks & Engineering Backlog** | Active sprint tasks, urgency rankings, and status register. | [`docs/TASKS.md`](docs/TASKS.md) |
| **Version Control & Changelog** | Git workflow, Conventional Commits, migration history (0001–0021), and SemVer changelog. | [`docs/version-control.md`](docs/version-control.md) |

---

## 🛠️ Reference Implementation Tech Stack (v0 Prototype)
- **Backend**: Python / Django (Server-rendered templates + Django REST Framework API for mobile clients)
- **Database**: PostgreSQL (Relational schema with hybrid time granularity and strict row-level security)
- **Security**: AES-256-GCM application-level field encryption for booking confirmation codes and door PINs.
- **Persistence & Sync**: Bi-directional file synchronization with canonical markdown archives in `Trips/*.md`.

---

## 🚀 Quickstart & Development Setup

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
python manage.py makemigrations core
python manage.py migrate
```

### 5. Run Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.
