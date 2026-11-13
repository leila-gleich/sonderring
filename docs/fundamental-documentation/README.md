# Fundamental Documentation — Sonderring Architecture

> **Directory Status**: Canonical Architecture & Deep-Dive Specifications  
> **Traceability**: Complements [`docs/PRD.md`](../PRD.md), [`docs/DATA_MODEL.md`](../DATA_MODEL.md), [`docs/PAGE_OUTLINE.md`](../PAGE_OUTLINE.md), and [`AGENTS.md`](../../AGENTS.md).

---

## Purpose

The `docs/fundamental-documentation/` folder contains foundational architectural blueprints, extensibility analyses, and core design rationales that govern how Sonderring is built, expanded, and maintained across its dimensions.

While top-level docs (`PRD.md`, `DATA_MODEL.md`, `PAGE_OUTLINE.md`) define active system specifications, documents in this directory explain:
1. **System Extensibility**: How existing data structures permit future feature expansions without breaking backward compatibility.
2. **Architectural Decisions**: Why certain attributes or boundaries are structured as they are (e.g., UI Input vs. DB Attribute).
3. **Deep-Dive Implementation Guides**: Detailed technical roadmaps for complex or multi-layered tasks.

---

## Index of Fundamental Specifications

| Document | Focus Area | Status | Key Topics |
| :--- | :--- | :---: | :--- |
| [`stay-time-attributes-architecture.md`](stay-time-attributes-architecture.md) | **Stay Dimension** | Canonical | Check-in / Check-out time extensibility, `DateTimeField` schema preservation, UI input separation, and `TASK-003` roadmap. |
