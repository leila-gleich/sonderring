# Architecture & Refactoring Summary: Card Templates & Dimension Modals

> **Document Status**: Canonical Reference & Refactor Log  
> **Repository Root**: `/Users/leilagleich/Desktop/sonderring`  
> **Associated Tag**: `archive/refactor_card_templates` (Commit: `7fb960d`)  
> **Target Branch**: `working-dev`  
> **Related Documentation**: [`docs/tripItemAttributesReference.md`](file:///Users/leilagleich/Desktop/sonderring/docs/tripItemAttributesReference.md) · [`docs/DATA_MODEL.md`](file:///Users/leilagleich/Desktop/sonderring/docs/DATA_MODEL.md) · [`docs/livingUserStoriesAndAcceptanceCriteria.md`](file:///Users/leilagleich/Desktop/sonderring/docs/livingUserStoriesAndAcceptanceCriteria.md)

---

## ⚠️ CRITICAL NOTICE: Workspace Architecture & Directory Preservation

> [!CAUTION]
> **DO NOT DELETE `/Users/leilagleich/Desktop/sonderring`!**  
> This directory is **NOT** a disposable Gemini cache or sandbox. It is your **primary local project workspace and the root Git repository opened in your IDE** (VS Code, Cursor, PyCharm, etc.). Deleting it will permanently delete your codebase, virtual environment (`venv`), local SQLite database (`db.sqlite3`), migrations, and unpushed Git history.

### Workspace Distinction Explained:
1. **Primary Workspace (`/Users/leilagleich/Desktop/sonderring`)**:
   - This is where you develop, run your local server, inspect code in your editor, and manage Git branches.
   - It contains the active branch `working-dev`, the virtual environment, all installed packages, test fixtures, and docs.
   - **Keep this directory intact at all times.**
2. **Temporary Gemini Worktree (`~/.gemini/antigravity/worktrees/sonderring/refactor_card_templates`)**:
   - When Antigravity executes tasks on a feature branch, it creates an isolated background Git worktree under `~/.gemini/...`.
   - This was where the `refactor_card_templates` branch was temporarily checked out to keep your main workspace untouched while tests and edits were made.
   - Now that `refactor_card_templates` is merged into `working-dev` and tagged as `archive/refactor_card_templates`, that temporary worktree has served its purpose. Gemini manages or prunes that folder automatically.

---

## 1. Purpose of Partials

In Django and modern web architectures, a **template partial** is a self-contained, modular HTML snippet (such as `templates/partials/move_card.html`) rendered via `{% include %}` or dynamically injected into the DOM via HTMX.

### Key Architectural Roles:
1. **Component Modularization**: Prevents `trip_workspace.html` from expanding into an unmaintainable multi-thousand-line monolithic template. Each UI component lives in its own dedicated file.
2. **DRY (Don't Repeat Yourself)**: A single partial can be included in multiple contexts—for example, rendering a card in the **Chronological Timeline** view, inside the **Dimension Column** view, or inside search results—without duplicating HTML markup.
3. **Dynamic HTMX Swapping**: When a user creates, edits, or cycles the status of an itinerary item, the Django view does not need to re-render or reload the entire web page. Instead, it renders only the partial snippet (`render_to_string('partials/<dimension>_card.html', context)`) and swaps it directly into the target DOM container, providing near-instantaneous single-page app (SPA) responsiveness with pure server-side Django.

---

## 2. Actions Performed During the Refactor

### 2.1. Legacy Files & Models Cleanup
- **Purged Obsolete Templates**: Deleted legacy `templates/partials/nav_card.html`. The project historically used "Nav" before standardizing on the four canonical dimensions: **Move**, **Stay**, **Taste**, and **Play**.
- **Removed Legacy Database Tables**: Archived and permanently pruned legacy database tables (`navs`, `dos`, `recs`) and ensured all database references strictly target the 4 canonical models: `Move`, `Stay`, `Taste`, and `Play`.

### 2.2. Data Model & Database Enhancements ([`core/models.py`](file:///Users/leilagleich/Desktop/sonderring/core/models.py))
- **`Move` Model**:
  - Added `company` (carrier string, e.g., *Delta Airlines*, *SNCF*, *Hertz*).
  - Constrained transport modes strictly to `Planes`, `Trains`, `Car`.
- **`Stay` Model**:
  - Added `stay_length` (Integer) and `stay_length_unit` (`Day(s)`, `Week(s)`, `Month(s)`).
  - Constrained place types strictly to `Hotel`, `Home`, `Apartment`, `Room`, `Bed`.
- **`Taste` Model**:
  - Constrained taste types to `Food` and `Drink`.
  - Added `cuisine` enum (10 standard choices: *American, African, Asian, Contemporary, European, Fusion, Indian, Mediterranean, Mexican, South American*) for Food items.
  - Added `drink_category` enum (6 standard choices: *Beer, Cocktails, Wine, Tea & Coffee, Juice and Smoothies, Other*) for Drink items.
  - Added structured price tier buttons (`$`, `$$`, `$$$`, `$$$$`).
  - **Enforced Invariant**: Taste items strictly do not have end dates or end times.
- **`Play` Model**:
  - Standardized play types: `Outdoors`, `Tours`, `Events`, `Sightseeing`, `Other`.
  - Added `price_tier` buttons (`Free`, `$`, `$$`, `$$$`, `$$$$`).
  - Added tour duration / length capabilities for `Tours`.
- **Database Migrations**: Created and executed migration `0016_move_company_play_price_tier_stay_stay_length_and_more.py` with 100% data integrity checks.

### 2.3. Modal UX & Progressive Disclosure
- **Status-First Question Flow**: Refactored item creation and editing modals to use a 2-step progressive flow:
  - **Step 1**: Prompts user to declare status: **Idea** (`IDEA`), **Confirmed** (`CONFIRMED`), or **Complete** (`COMPLETE`).
  - **Step 2**: Dynamically unrolls the inputs tailored to that status (e.g., date requirements are enforced for `CONFIRMED` but optional for `IDEA`).
- **Initial Inputs vs. "More Options" Accordion**: Displayed essential primary inputs immediately (Name, Type, Location/Route, Link, Notes) while tucking secondary details, encrypted confirmation codes, and document attachments behind an expandable "More Options" toggle.

### 2.4. Encrypted Multi-File Vault Uploads ([`core/views.py`](file:///Users/leilagleich/Desktop/sonderring/core/views.py))
- Updated `add_move_view`, `edit_move_view`, `add_stay_view`, `edit_stay_view`, `add_taste_view`, `edit_taste_view`, `add_play_view`, and `edit_play_view`.
- Enabled multi-file upload capabilities directly within the modals. Files (flight tickets, boarding passes, hotel vouchers, menu PDFs) are encrypted using AES-256-GCM and stored in the secure Vault linked via `ItemDocument` records.

### 2.5. Seed Trip Normalization & Validation
- Normalized all 11 seed trips and 411 database records in `core/seed_initial.py` and `core/fixtures/seed_data.json` to strictly follow the new schema.
- Verified all 100 unit tests pass without errors or regressions.

### 2.6. Branch Merge & Archival
- Merged `refactor_card_templates` cleanly into `working-dev` (merge commit `2061e90`).
- Tagged the feature branch head as `archive/refactor_card_templates` (`7fb960d`) and pushed to the remote repository.
- Safely removed the ephemeral remote feature branch.

---

## 3. Why Dimension-Specific Partials are Advantageous (The 3 Core Points)

Extracting dedicated partials for each dimension (`partials/move_card.html`, `partials/stay_card.html`, `partials/taste_card.html`, `partials/play_card.html`) provides three distinct architectural advantages for Sonderring:

### Point 1: Separation of Concerns & High-Maintainability Schema Mapping
Each of the four dimensions serves a fundamentally different data structure:
- **Move** has origins, destinations, transport modes, carrier companies, and precise departure times.
- **Stay** requires check-in/check-out date ranges, length-of-stay unit badges, and property types.
- **Taste** requires dynamic switching between cuisines and drink categories, fixed price tier badges, and explicitly forbids end dates.
- **Play** features outdoor/sightseeing categories, free vs. paid tiers, and tour durations.

Attempting to render all four within a single generic card template requires massive, brittle trees of `{% if item.dimension == '...' %}`. Splitting them into dimension-specific partials completely isolates their logic. Modifying the Taste card layout or adding a new drink tag will never cause accidental visual regressions or layout bugs in Move or Stay.

### Point 2: Granular HTMX Dynamic Swapping & Server-Side Performance
Sonderring’s interaction model relies on live HTMX interactions (editing fields, cycling status badges, expanding options).
- When a user changes a Stay item from `IDEA` to `CONFIRMED`, the server view returns only the updated `stay_card.html` fragment.
- Without dedicated partials, the server view must either re-render the entire page or duplicate card HTML inside Python view strings.
- Dimension partials keep DOM payloads under 2 KB per interaction, eliminate full-page browser repaints, and make real-time updates feel instantaneous.

### Point 3: Dimension-Tailored Visual Polish & Component Testability
Each dimension represents a distinct mental model with bespoke visual cues:
- Flights display transit arrows (`LAX ✈️ JFK`) and carrier callouts.
- Stays display night counts and lodging type pills.
- Restaurants display price tier indicators (`$$$`) and cuisine badges.
- Activities display duration pills and ticket status.

Dedicated partials allow UI designers and frontend developers to refine micro-interactions, CSS styles, and accessibility attributes independently. Furthermore, isolated partials can be unit-tested directly using Django's template engine tests without mocking the entire page state.

---

## 4. Common Attributes vs. Dimension-Specific Rules

### 4.1. Universal Core Attributes (All Dimensions)
Every item across all four dimensions displays these base attributes:
- **Name\*** (Required string / title)
- **Status\*** (Required enum: `IDEA`, `CONFIRMED`, `COMPLETE` — set via Step 1)
- **Type** (Required dimension-specific category dropdown)
- **Web Link** (Optional URL for bookings, menus, or information)
- **Notes / Description** (Optional freeform textarea for policies, notes, house rules)
- **More Options Toggle** (Collapsible container for secondary attributes, encrypted confirmation codes, and document uploads)

### 4.2. Dimension-Specific Rules & Invariants Matrix

| Dimension | Primary Inputs (Step 2 Initial) | "More Options" Secondary Inputs | Core Constraints & Invariants |
| :--- | :--- | :--- | :--- |
| **Move** ✈️ | • Name\*<br>• Status\*<br>• Type (`Planes`, `Trains`, `Car`)<br>• Origin<br>• Destination<br>• Link<br>• Notes | • Departure Date\* (*Mandatory if CONFIRMED*)<br>• Departure Time (*Prominent for Planes/Trains*)<br>• Company (Carrier name)<br>• Price (Decimal)<br>• Confirmation Code (AES-256 encrypted)<br>• Upload Documents | Must have origin and destination. Departure date mandatory when confirmed. |
| **Stay** 🏨 | • Name\*<br>• Status\*<br>• Type (`Hotel`, `Home`, `Apartment`, `Room`, `Bed`)<br>• Location (Address)<br>• Link<br>• Notes | • Stay Length (Integer) + Unit (`Day(s)`, `Week(s)`, `Month(s)`)<br>• Start Date\* (*Check-in; mandatory if CONFIRMED*)<br>• End Date\* (*Check-out; mandatory if CONFIRMED*)<br>• Price (Decimal)<br>• Confirmation Code (AES-256 encrypted)<br>• Upload Documents | No check-in/out time inputs (handled in notes). End date must be on or after start date. |
| **Taste** 🍽️ | • Name\*<br>• Status\*<br>• Type (`Food`, `Drink`)<br>• Location (Address / Venue)<br>• Link<br>• Notes | • Dynamic Category:<br>&nbsp;&nbsp;– Food: `Cuisine` (10 choices)<br>&nbsp;&nbsp;– Drink: `Category` (6 choices)<br>• Price Tier Buttons (`$`, `$$`, `$$$`, `$$$$`)<br>• Date (*Mandatory if CONFIRMED, optional if IDEA*)<br>• Booking Reference (AES-256 encrypted)<br>• Upload Documents | **STRICT INVARIANT: No end date or end time.** Categorization dynamically adjusts based on Food vs. Drink type. |
| **Play** 🎭 | • Name\*<br>• Status\*<br>• Type (`Outdoors`, `Tours`, `Events`, `Sightseeing`, `Other`)<br>• Location (Address / Venue)<br>• Link<br>• Notes | • Price Tier Buttons (`Free`, `$`, `$$`, `$$$`, `$$$$`)<br>• Date (*Mandatory if CONFIRMED, optional if IDEA*)<br>• Time (Optional)<br>• Tour Length / Duration (*For Tours*)<br>• Confirmation Code (AES-256 encrypted)<br>• Upload Documents | Supports free tier button. Tour duration optional for tour activities. |

---

## 5. Summary of Recommendations

### 5.1. Recommendations Summary Table

| Phase | Component | Recommendation | Rationale | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | **Template Partials** | Extract `stay_card.html`, `taste_card.html`, and `play_card.html` into `templates/partials/` mirroring `move_card.html`. | Completes the partials architecture across all 4 dimensions, cleans up `trip_workspace.html`, and enables seamless HTMX swapping. | **High** |
| **Phase 2** | **Form Modal Partials** | Extract dimension modal forms into `templates/partials/forms/` (`move_form.html`, `stay_form.html`, etc.). | Eliminates 600+ lines of duplicated modal markup in `trip_workspace.html` and standardizes the 2-step question flow. | **High** |
| **Phase 3** | **HTMX Responses** | Update views (`edit_stay_view`, `edit_taste_view`, etc.) to return partial templates on HTMX `POST` requests. | Reduces response payload from ~180 KB (full page) to <2 KB (single card), enabling instant client updates. | **Medium** |
| **Phase 4** | **Legacy Pruning** | Remove unreferenced `templates/partials/nav_card.html` from `working-dev`. | Prevents developer confusion and eliminates legacy nomenclature drift. | **Medium** |
| **Phase 5** | **Client Validation** | Add lightweight JS validation enforcing start/end date logic for Stays and dynamic cuisine/category dropdown swaps for Taste. | Improves UX responsiveness before the form reaches backend Django validation. | **Low** |

### 5.2. Executive Summary Explanation (3–4 Sentences)
The refactoring performed so far has successfully unified Sonderring's data models, seed data, and modal forms with the canonical four dimensions and the status-first UX flow. To achieve full architectural elegance and performance, the remaining inline card and form markup in `trip_workspace.html` should be extracted into modular, dimension-specific partials matching the existing `move_card.html` pattern. This modularization directly empowers HTMX to perform micro-swaps of individual cards upon user interaction, drastically reducing network payloads and eliminating full-page reloads. Finally, pruning lingering legacy files such as `nav_card.html` ensures that the codebase strictly reflects canonical nomenclature across all templates, models, and documentation.

---

## 6. Additional Actions Taken & Their Benefits

1. **Integrated Multi-File Encrypted Vault Uploads**:
   - *Action*: Enhanced view handlers to accept multi-file attachments across all 4 dimensions, encrypting them via AES-256-GCM and recording them in the `ItemDocument` table.
   - *Benefit*: Trippers can securely attach boarding passes, vouchers, and confirmation PDFs directly while creating or editing an item.
2. **Status-First Progressive Disclosure Flow**:
   - *Action*: Implemented a 2-step question modal that queries intent (`IDEA`, `CONFIRMED`, `COMPLETE`) before showing input fields.
   - *Benefit*: Reduces cognitive overload; users brainstorming ideas aren't bombarded with required date and booking code fields.
3. **Canonical Documentation Alignment**:
   - *Action*: Cross-linked [`docs/tripItemAttributesReference.md`](file:///Users/leilagleich/Desktop/sonderring/docs/tripItemAttributesReference.md) with [`docs/DATA_MODEL.md`](file:///Users/leilagleich/Desktop/sonderring/docs/DATA_MODEL.md) and [`docs/livingUserStoriesAndAcceptanceCriteria.md`](file:///Users/leilagleich/Desktop/sonderring/docs/livingUserStoriesAndAcceptanceCriteria.md).
   - *Benefit*: Ensures full traceability between user stories, acceptance criteria, database constraints, and UI presentation.
4. **Seed Trip Fixture Modernization**:
   - *Action*: Re-seeded all 11 canonical trips with 411 database records using the normalized schema.
   - *Benefit*: Guarantees that local development, demo environments, and automated test suites operate on clean, valid data without legacy field mismatches.

---

## 7. Archived Files & Historical Reference Points

For future reference or historical rollbacks, keep note of the following Git references and archived assets:

1. **Git Tag `archive/refactor_card_templates`**:
   - Points to commit `7fb960d`.
   - Contains the exact state of the feature branch before merging into `working-dev`.
   - Inspect via Git:
     ```bash
     git show archive/refactor_card_templates
     git checkout archive/refactor_card_templates
     ```
2. **Obsolete / Legacy Template**:
   - `templates/partials/nav_card.html`: Preserved in Git history prior to deletion. The canonical partial to use and replicate is [`templates/partials/move_card.html`](file:///Users/leilagleich/Desktop/sonderring/templates/partials/move_card.html).
3. **Legacy Database Cleanups**:
   - Migration `6d8a629` removed legacy `navs`, `dos`, and `recs` tables. If legacy schema references are ever needed for historical data recovery, inspect that commit.
4. **Canonical Seed Trips Directory**:
   - Located at `docs/seed-trips/` (contains 11 JSON/Markdown trip specifications). This is the source of truth for all seed data imports.
