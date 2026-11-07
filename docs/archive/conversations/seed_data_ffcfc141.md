# Conversation Archive: Seed Data & Canonical Trips Standard

> **Document Status**: Canonical Archive  
> **Original Conversation ID**: `ffcfc141-fccb-4da1-ac87-07056224aa49`  
> **Session Title**: Seed Data  
> **Project Scope**: Creation of self-contained `docs/seed-trips/`, schema token formatting standards, and eradication of fabricated trip details.  
> **Related Files**: [`docs/seed-trips/`](file:///Users/leilagleich/Desktop/sonderring/docs/seed-trips/) · [`docs/tripItemAttributesReference.md`](file:///Users/leilagleich/Desktop/sonderring/docs/tripItemAttributesReference.md) · [`core/seed_initial.py`](file:///Users/leilagleich/Desktop/sonderring/core/seed_initial.py)

---

## 1. Executive Summary & Core Intent

This conversation was initiated to systematically audit, correct, and standardize Sonderring's seed trip data. Previously, external trip markdown files contained fabricated details (e.g., mistaking New Year's Eve in San Diego for New York, incorrect dates for Hawaii, and invented amenities or hotel venues). 

The user redirected the architecture toward four foundational engineering priorities:
1. **Authenticity**: Every single trip item, flight, stay, restaurant, and activity must represent verified, real-world data matching user records. Zero fabricated data.
2. **Conciseness**: Overly florid, verbose descriptions (e.g. *"High-elevation mountain parkway drive through rock tunnels..."*) were eliminated in favor of clean, direct descriptions (*"Mountain parkway with good views"*).
3. **Standardization**: Strict date-first naming (`yy-mm-[trip-name].md`), uniform 4-dimension section headers (`Trip MetaData`, `Move`, `Stay`, `Taste`, `Play`), and consistent casing.
4. **Self-Containment**: Decoupling the codebase from external folders (`/Desktop/Trips`) by establishing `docs/seed-trips/` directly within the Git repository.

---

## 2. Key Architecture Standards Established

### 2.1. Selective Schema Token Formatting (Markdown Best Practice)
To clearly distinguish controlled database enum choices and system identifiers from open-ended human prose:
- **Controlled Database Enums**: Wrapped in backticks with uppercase representation:
  - `Status: `CONFIRMED``, `Status: `IDEA``
  - `Time Granularity: `EXACT_RANGE``, `Time Granularity: `MONTH``
  - `Type: `Planes``, `Type: `Hotel``, `Type: `Food``
- **Alphanumeric Identifiers**: Wrapped in backticks:
  - `Flight: `DL 2661``
  - `Origin: `LAX``, `Destination: `AVL``
  - `Confirmation/Reference: `3208541836``
- **Human Prose / Non-Constrained Fields**: Plaintext (Names, Dates, Locations, Prices, Descriptions, Notes).

### 2.2. Dimension-Specific Rules & Invariants
- **Move ✈️**:
  - Flight names standardized to `Flight to [Destination]` (omitting intermediate layover names).
  - Explicit `Origin` and `Destination` fields added; removed meaningless "direction" fields.
  - Tours/trolleys removed from Move and categorized under Play.
- **Stay 🏨**:
  - Check-in and check-out times **omitted entirely** (only `Start Date` and `End Date` allowed). Property check-in rules live in `Notes`.
  - Field renamed from `Address` to `Location`.
  - Amenities removed as a separate model field and placed into `Notes` until formalized.
- **Taste 🍽️**:
  - Strictly **no end date or end time**.
  - Price buttons standardized: `$`, `$$`, `$$$`, `$$$$`.
- **Play 🎭**:
  - Price tiers: `Free`, `$`, `$$`, `$$$`, `$$$$`.
  - Support for time ranges rather than start/end calendar dates.

### 2.3. Universal Naming & Status
- **`Confirmation/Reference`**: Standardized label across all dimensions (replacing "booking code", "confirmation number", etc.).
- **Item Status**: Limited strictly to `CONFIRMED` or `IDEA` for seed data. `COMPLETE` was forbidden in seed templates.

---

## 3. Chronological Progression of the Conversation

1. **Audit & Scope Definition (Turns 1–9)**:
   - User identified fabrication in historical markdown files (NYE, Hawaii dates, phantom car rentals).
   - Selected `21-12-Asheville.md` as the pilot template.
   - Refined flight naming (`Flight to Asheville`), dates (Dec 7–11), and verified hotel (*Hilton Garden Inn Asheville Downtown*, confirmation `3208541836`).
   - Established uppercase enum token formatting rule (`Status: `CONFIRMED``).
2. **Sequential Seed Trip Restructuring (Turns 10–21)**:
   - `21-12-NYE.md`: Reconstructed Tiffany’s flight, drive to San Diego, music events (*Desert Hearts* confirmed, *Eli & Fur* idea), and dinner locations.
   - `21-10-JT.md` & `22-01-JT.md`: Sourced verified Airbnbs from user's Google Sheet, confirmed *Ocotillo Poet's Rest*, added tripper Catherine.
   - `21-07-Flame.md`, `26-08-Hawaii.md`, `26-10-Halloween-Staycation.md`, `26-10-Iceland.md`: Standardized dates, car rentals, and flight items.
   - `26-09-Malticilia.md`: Moved *Upper Barrakka Gardens* and walking tours to Play; added verified boat outings in Ortigia and Malta.
3. **Database Integration & Git Decoupling (Turns 22–26)**:
   - Audited live website against the 9 trip files.
   - Created Django management command [`import_seed_trips`](file:///Users/leilagleich/Desktop/sonderring/core/management/commands/import_seed_trips.py) to ingest canonical markdown directly from `docs/seed-trips/`.
   - Exported normalized database state to `core/fixtures/seed_data.json`.
   - Guaranteed full repository independence: zero external directory dependencies.

---

## 4. Key Artifacts Generated from this Session

- **Canonical Trip Specifications**: [`docs/seed-trips/`](file:///Users/leilagleich/Desktop/sonderring/docs/seed-trips/) (initially 9, expanded to 11 trips).
- **Core Seeding Script**: [`core/seed_initial.py`](file:///Users/leilagleich/Desktop/sonderring/core/seed_initial.py).
- **Master Fixture Database**: [`core/fixtures/seed_data.json`](file:///Users/leilagleich/Desktop/sonderring/core/fixtures/seed_data.json).
- **Attributes Specification**: [`docs/tripItemAttributesReference.md`](file:///Users/leilagleich/Desktop/sonderring/docs/tripItemAttributesReference.md).
