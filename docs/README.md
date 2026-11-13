# Sonderring — Canonical Living Documentation Hub

Welcome to the authoritative living documentation suite for **Sonderring**, the collaborative trip-planning application engineered for friend groups to coordinate travel logistics across four universal pillars—**Move** (transportation), **Stay** (accommodations), **Taste** (food & dining), and **Play** (activities & sightseeing)—while enforcing zero-knowledge security standards for booking confirmation codes and travel documents.

This directory serves as the **single source of truth** for product managers, software engineers, security architects, and AI assistants working on the Sonderring platform.

---

## 🧭 Foundational Pillars

All design specifications, data models, and features in Sonderring strictly adhere to four foundational pillars established in [`AGENTS.md`](../AGENTS.md):

1. **Authenticity**: Absolute fidelity to real-world travel facts. Zero tolerance for fabricated itinerary items, placeholder hallucinations, or assumed reservations.
2. **Conciseness**: Maximum signal, minimum noise. Functional, brief notes over marketing hyperbole.
3. **Standardization**: Strict domain naming across dimensions (**Move**, **Stay**, **Taste**, **Play**), uniform field names (`Location`, `Confirmation/Reference`), and deterministic readiness states (`IDEA` $\rightarrow$ `CONFIRMED` $\rightarrow$ `COMPLETE`).
4. **Transparency**: Explicit provenance and public tracking of all architectural backlog tasks in [`TASKS.md`](TASKS.md).

---

## 📚 Master Living Documentation Index

| Document | Scope & Focus Area | Key Contents |
| :--- | :--- | :--- |
| [**`PRD.md`**](PRD.md) | **Product Requirements Document** | High-level product vision, user personas, functional requirements across dimensions, non-functional security/performance requirements, and traceability. |
| [**`DATA_MODEL.md`**](DATA_MODEL.md) | **Canonical Relational Data Model** | Entity-Relationship Diagrams (Mermaid), relational table definitions, check constraints, `v_itinerary_items` SQL view, and state machines. |
| [**`CYBERSECURITY.md`**](CYBERSECURITY.md) | **Cybersecurity & Threat Model** | AES-256-GCM field encryption, Document Vault access control, STRIDE threat model, and SHA-256 tamper-evident audit log chaining. |
| [**`PAGE_OUTLINE.md`**](PAGE_OUTLINE.md) | **Site Architecture & UI Flows** | Screen-by-screen breakdown, 6 workspace tabs (Timeline, Move, Stay, Taste, Play, Vault), status-first item creation flows, and responsive UI. |
| [**`livingUserStoriesAndAcceptanceCriteria.md`**](livingUserStoriesAndAcceptanceCriteria.md) | **Living User Stories & AC** | Active user stories, testable acceptance criteria, universal author sovereignty, and full traceability matrix. |
| [**`tripItemAttributesReference.md`**](tripItemAttributesReference.md) | **Dimensional Attribute Catalog** | Exact database attributes vs. form input controls across Move, Stay, Taste, and Play dimensions. |
| [**`API_SPECIFICATION.md`**](API_SPECIFICATION.md) | **RESTful API Contract** | Endpoint routes, JSON request/response payloads, authentication envelopes, and error codes for web and future mobile clients. |
| [**`MARKDOWN_SYNC_SPEC.md`**](MARKDOWN_SYNC_SPEC.md) | **Bidirectional Markdown Sync** | Markdown grammar, section parsing, DB-to-file serialization rules, and deterministic synchronization protocols. |
| [**`MVP.md`**](MVP.md) | **MVP Scope & Multi-Phase Roadmap** | Phase 1 (MVP In-Scope) features vs. Phase 2 (Live Flight APIs, Places autosuggest) and Phase 3 (Mobile native apps). |
| [**`TASKS.md`**](TASKS.md) | **Engineering Backlog & Tasks** | Active sprint tasks, urgency levels, status register (`To Do`, `In Progress`, `Complete`), and documentation update obligations. |
| [**`version-control.md`**](version-control.md) | **Version Control & Changelog** | Git branching model, Conventional Commits standard, PostgreSQL migration governance (0001–0021), and release history (`v0.1.0`–`v0.8.0`). |
| [**`refactorCardTemplatesSummary.md`**](refactorCardTemplatesSummary.md) | **UI Architecture Refactor** | Technical review of modular card template partials (`stay_card.html`, `move_card.html`, etc.) and interactive status pills. |

---

## 🗂️ Architectural Deep Dives & Reference Catalogs

* **[`fundamental-documentation/`](fundamental-documentation/README.md)**:
  * [`stay-time-attributes-architecture.md`](fundamental-documentation/stay-time-attributes-architecture.md) — Stay dimension check-in/out time extensibility, `DateTimeField` preservation, and UI input separation.
* **[`seed-trips/`](seed-trips/README.md)**:
  * Canonical markdown representations of real-world travel trips (`26-09-Malticilia.md`, `26-10-Iceland.md`, `21-12-Asheville.md`, `Japan.md`, etc.) bidirectionally synchronized with PostgreSQL.
* **[`tripspace-nomenclature.svg`](tripspace-nomenclature.svg)**:
  * Official visual nomenclature diagram mapping the hierarchy: **TripSpace $\rightarrow$ Dimension $\rightarrow$ Item $\rightarrow$ Category & Attributes**.

---

## 🔄 Documentation Maintenance Protocol

1. **Always Update Specs Alongside Code**: Never alter database models, form fields, or role permissions without updating the corresponding specification document in this directory.
2. **Relative Link Portability**: All internal cross-references must use relative Markdown links (e.g., `[PRD](PRD.md)` or `[models.py](../core/models.py)`) rather than machine-specific absolute file URLs.
3. **Pillars Compliance**: All documentation additions must maintain fidelity to the four foundational pillars: Authenticity, Conciseness, Standardization, and Transparency.
