# Sonderring Engineering & Feature Tasks

> **Document Status**: Canonical Backlog  
> **Traceability**: Linked to [`docs/PRD.md`](PRD.md), [`docs/DATA_MODEL.md`](DATA_MODEL.md), [`docs/livingUserStoriesAndAcceptanceCriteria.md`](livingUserStoriesAndAcceptanceCriteria.md), and [`AGENTS.md`](../AGENTS.md).

## Quick Tasks
This area is to quickly add short tasks
* Home shouldn't be the same page as all tripspaces
* change UX for status and form flow
---

## 📌 Task Status Reference
Every task is tracked through one of three statuses:
- **`To Do`**: Backlogged or planned work not yet active.
- **`In Progress`**: Work currently being designed, specified, or implemented.
- **`Complete`**: Work verified, tested, and shipped.

Urgency levels: **`Low`** | **`Medium`** | **`High`**

---

## 📋 Task Register

| ID | Title | Dimension / Area | Urgency | Status | Documents to Update Upon Completion | Created |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **TASK-001** | Add Amenities as a Native Attribute for Stay Items | Stay | Low | `To Do` | `DATA_MODEL.md`, `PAGE_OUTLINE.md`, `MARKDOWN_SYNC_SPEC.md`, `tripItemAttributesReference.md`, `livingUserStoriesAndAcceptanceCriteria.md` | 2026-11-01 |
| **TASK-002** | Update Documentation for TripSpace Dimensions | Core / Cross-Dimension | Medium | `To Do` | `PAGE_OUTLINE.md`, `DATA_MODEL.md`, `PRD.md`, `tripItemAttributesReference.md`, `AGENTS.md`, `livingUserStoriesAndAcceptanceCriteria.md` | 2026-11-01 |
| **TASK-003** | Support Check-in and Check-out Time Attributes for Stay Items | Stay | Low | `To Do` | `fundamental-documentation/stay-time-attributes-architecture.md`, `tripItemAttributesReference.md`, `PAGE_OUTLINE.md`, `MARKDOWN_SYNC_SPEC.md`, `livingUserStoriesAndAcceptanceCriteria.md` | 2026-11-01 |
| **TASK-004** | Inline Dropdown for Item Creation Status Selection | UI / Item Creation | Medium | `To Do` | `PAGE_OUTLINE.md`, `tripItemAttributesReference.md`, `livingUserStoriesAndAcceptanceCriteria.md` | 2026-11-02 |
| **TASK-005** | Clickable Status Pill & Removal of Arrow Buttons for Item Status Changes | UI / Item Cards | Medium | `To Do` | `PAGE_OUTLINE.md`, `livingUserStoriesAndAcceptanceCriteria.md` | 2026-11-02 |
| **TASK-006** | Self-Contained Canonical Seed Trips Ingestion & Decoupling | Core / Data & Sync | High | `Complete` | `MARKDOWN_SYNC_SPEC.md`, `DATA_MODEL.md`, `AGENTS.md`, `livingUserStoriesAndAcceptanceCriteria.md` | 2026-11-05 |

---

## 📝 Task Details

### TASK-001: Add Amenities as a Native Attribute for Stay Items
* **ID**: `TASK-001`
* **Area / Dimension**: `Stay`
* **Status**: `To Do`
* **Urgency**: `Low`
* **Date Added**: 2026-11-01
* **Documents to Update Upon Completion**:
  - [`docs/DATA_MODEL.md`](DATA_MODEL.md) (Add `amenities` attribute to `Stay` model schema)
  - [`docs/tripItemAttributesReference.md`](tripItemAttributesReference.md) (Add Stay Amenities field and input specifications)
  - [`docs/PAGE_OUTLINE.md`](PAGE_OUTLINE.md) (Update Stay creation/edit modal inputs)
  - [`docs/MARKDOWN_SYNC_SPEC.md`](MARKDOWN_SYNC_SPEC.md) (Update Stay markdown parser and serializer)
  - [`docs/livingUserStoriesAndAcceptanceCriteria.md`](livingUserStoriesAndAcceptanceCriteria.md) (Synchronize acceptance criteria for Stay item creation and editing)
* **Context**:
  Currently, stay amenities (e.g., gym, shuttle, pool, laundry, restaurant) are preserved inside the `Notes` field of Stay items as plaintext (e.g., `"Amenities: Gym, shuttle, laundry, restaurant"`).
* **Objective**:
  Promote amenities from an unstructured note into a first-class model attribute and UI form control for Stay items.
* **Scope & Implementation Notes**:
  1. **Data Model**: Add an `amenities` field (e.g., `JSONField`, `ArrayField`, or comma-delimited string/tags) to the Stay Django model in `core/models.py`.
  2. **UI Input**: Add an amenities tag-selector or multi-select input in the Stay creation and edit modals.
  3. **Markdown Sync**: Update serializer and parser in `MARKDOWN_SYNC_SPEC.md` to support `* Amenities: ...` on Stay items.
  4. **Data Migration**: Parse existing Stay notes to extract legacy `"Amenities: ..."` strings into the new attribute.

### TASK-002: Update Documentation for TripSpace Dimensions
* **ID**: `TASK-002`
* **Area / Dimension**: `Core / Cross-Dimension`
* **Status**: `To Do`
* **Urgency**: `Medium`
* **Date Added**: 2026-11-01
* **Documents to Update Upon Completion**:
  - [`docs/PAGE_OUTLINE.md`](PAGE_OUTLINE.md) (Dimension views, column/section layouts, notes containers, and status-first modal flows)
  - [`docs/DATA_MODEL.md`](DATA_MODEL.md) (TripSpace structure, dimension associations, item taxonomy, and readiness states)
  - [`docs/PRD.md`](PRD.md) (TripSpace domain definitions, 4 dimensions, and functional requirements)
  - [`docs/tripItemAttributesReference.md`](tripItemAttributesReference.md) (Item attributes vs UI inputs across Move, Stay, Taste, Play)
  - [`AGENTS.md`](../AGENTS.md) (Nomenclature, dimension views, and item input vs attribute boundaries)
  - [`docs/livingUserStoriesAndAcceptanceCriteria.md`](livingUserStoriesAndAcceptanceCriteria.md) (Synchronize living user stories and acceptance criteria for all dimension views and forms)
* **Context**:
  The architecture of TripSpaces is built upon four foundational dimensions: Move, Stay, Taste, and Play. As the project evolves, specifications around dimension views (UI layout, notes components, visual hierarchy), item forms/inputs (status-first modal workflows, input vs attribute boundaries), and the overall domain structure of a TripSpace require comprehensive, unified documentation.
* **Objective**:
  Conduct a systematic update and alignment of all documentation covering the overall structure of a TripSpace and its dimensions, including UI views, form workflows, and data relationships.
* **Scope & Implementation Notes**:
  1. **Overall TripSpace & Dimension Structure**:
     - Define and document the structural hierarchy: TripSpace (canvas) $\rightarrow$ Dimension (Move, Stay, Taste, Play) $\rightarrow$ Item $\rightarrow$ Category/Attributes.
     - Document dimension-level properties, readiness state lifecycles (`Idea`, `Confirmed`, `Complete`), and validation rules.
  2. **Dimension Views**:
     - Detail the workspace UI structure for each dimension (column/grid behavior, headers, icons, and dimension-level notes components).
     - Specify responsive layout behavior across desktop, tablet, and mobile views.
  3. **Views & Forms (Item Modals)**:
     - Document status-first creation and editing modal flows across all four dimensions.
     - Detail required vs optional fields per readiness state (e.g., date requirements in `Confirmed` vs optional in `Idea`).
     - Clarify the separation between frontend Item Inputs (UI controls) and backend Item Attributes (DB fields).
  4. **Cross-Document Traceability**:
     - Ensure synchronized terminology across `PRD.md`, `DATA_MODEL.md`, `PAGE_OUTLINE.md`, and `tripItemAttributesReference.md`.
     - Update `livingUserStoriesAndAcceptanceCriteria.md` to reflect the updated views, forms, and validation rules.

### TASK-003: Support Check-in and Check-out Time Attributes for Stay Items
* **ID**: `TASK-003`
* **Area / Dimension**: `Stay`
* **Status**: `To Do`
* **Urgency**: `Low`
* **Date Added**: 2026-11-01
* **Documents to Update Upon Completion**:
  - [`docs/fundamental-documentation/stay-time-attributes-architecture.md`](fundamental-documentation/stay-time-attributes-architecture.md) (Canonical architectural reference for stay time extensibility)
  - [`docs/tripItemAttributesReference.md`](tripItemAttributesReference.md) (Update Stay "More Options" specifications to include optional check-in/out times)
  - [`docs/PAGE_OUTLINE.md`](PAGE_OUTLINE.md) (Update Stay modal specifications to document optional time picker controls)
  - [`docs/MARKDOWN_SYNC_SPEC.md`](MARKDOWN_SYNC_SPEC.md) (Document optional stay check-in/out time parsing and serialization)
  - [`docs/livingUserStoriesAndAcceptanceCriteria.md`](livingUserStoriesAndAcceptanceCriteria.md) (Synchronize acceptance criteria for optional stay times)
* **Context**:
  The backend database schema in `core/models.py` natively supports check-in and check-out timestamps (`DateTimeField`) and disambiguation flags (`has_check_in_time`, `has_check_out_time`). The date-only convention in documentation was established as a UI simplification, not a schema limitation. See deep-dive analysis in [`docs/fundamental-documentation/stay-time-attributes-architecture.md`](fundamental-documentation/stay-time-attributes-architecture.md).
* **Objective**:
  Preserve backend schema capability and provide a clean pathway to expose optional check-in and check-out time controls in the UI and markdown synchronization engine.
* **Scope & Implementation Notes**:
  1. **Schema Preservation**: Maintain `check_in` and `check_out` as `DateTimeField` along with `has_check_in_time` and `has_check_out_time` boolean flags in `core/models.py`.
  2. **UI Form Controls**: Add optional time picker inputs (`#inputStayCheckInTime`, `#inputStayCheckOutTime`) under "More Options" in the Stay creation/edit modal.
  3. **Markdown Sync**: Update parser and serializer to support optional stay timestamps without breaking date-only files.
  4. **Validation**: Ensure date and time invariants ($check\_out \ge check\_in$) are respected.

### TASK-004: Inline Dropdown for Item Creation Status Selection
* **ID**: `TASK-004`
* **Area / Dimension**: `UI / Item Creation`
* **Status**: `To Do`
* **Urgency**: `Medium`
* **Date Added**: 2026-11-02
* **Documents to Update Upon Completion**:
  - [`docs/PAGE_OUTLINE.md`](PAGE_OUTLINE.md) (Update item creation flow from multi-step status modal to direct modal opening with status preset via dropdown)
  - [`docs/tripItemAttributesReference.md`](tripItemAttributesReference.md) (Update Section 2.1 Status-First Question Flow to reflect dropdown entry)
  - [`docs/livingUserStoriesAndAcceptanceCriteria.md`](livingUserStoriesAndAcceptanceCriteria.md) (Synchronize user stories and acceptance criteria for item creation UX)
* **Context**:
  Currently, creating an item triggers a two-step modal flow where "Step 1" prompts the user to select a readiness status (`Idea` vs `Confirmed` vs `Complete`) on an initial modal screen before transitioning to the item form. This creates unnecessary friction, layout shifting, and extra clicks during rapid trip planning.
* **Objective**:
  Enhance the item creation UX by replacing the separate modal status-selection screen with an inline dropdown directly accessible when initiating item creation.
* **Scope & Implementation Notes**:
  1. **Direct Trigger Dropdown**: Replace the separate "Step 1" modal screen with a dropdown trigger on the item creation button (e.g., a split button or click dropdown: `+ Add Item ▾` $\rightarrow$ `Idea`, `Confirmed`), or an inline status dropdown embedded in the item form header.
  2. **Direct Modal Presentation**: Selecting an option immediately opens the item modal pre-configured for that status, displaying only the relevant inputs without an interstitial step.
  3. **Cross-Dimension Consistency**: Standardize this creation pattern across all four dimensions (Move, Stay, Taste, Play).

### TASK-005: Clickable Status Pill & Removal of Arrow Buttons for Item Status Changes
* **ID**: `TASK-005`
* **Area / Dimension**: `UI / Item Cards`
* **Status**: `To Do`
* **Urgency**: `Medium`
* **Date Added**: 2026-11-02
* **Documents to Update Upon Completion**:
  - [`docs/PAGE_OUTLINE.md`](PAGE_OUTLINE.md) (Update card specifications: deprecate arrow cycle buttons, document interactive status pill)
  - [`docs/livingUserStoriesAndAcceptanceCriteria.md`](livingUserStoriesAndAcceptanceCriteria.md) (Update acceptance criteria for direct status transitions on cards)
  - Frontend templates / components (`core/templates/`): Update item card markup and asynchronous click handlers.
* **Context**:
  On existing item cards inside dimension views, transitioning an item between readiness states currently uses a "little arrows button" (or status cycle arrows). This causes visual noise, takes up card real estate, and is less intuitive than interacting directly with the status badge itself.
* **Objective**:
  Streamline card ergonomics and reduce visual clutter by removing the arrow buttons and making the status pill/badge directly clickable to change status.
* **Scope & Implementation Notes**:
  1. **Remove Arrow Controls**: Delete the cycle/arrow buttons from item cards across all dimension views (Move, Stay, Taste, Play).
  2. **Interactive Status Pill**: Make the status pill/badge (e.g., `Idea`, `Confirmed`) directly clickable with hover affordance (pointer cursor, subtle highlight).
  3. **Dropdown / Direct Toggle**: Clicking the status pill reveals a compact popover/dropdown allowing the traveler to switch statuses instantly (`Idea` $\leftrightarrow$ `Confirmed` $\leftrightarrow$ `Complete`).
  4. **Optimistic UI & API Update**: Trigger an asynchronous PATCH request to update item status and fluidly re-render or relocate the card across status sections without a full page refresh.

### TASK-006: Self-Contained Canonical Seed Trips Ingestion & Decoupling
* **ID**: `TASK-006`
* **Area / Dimension**: `Core / Data & Sync`
* **Status**: `Complete`
* **Urgency**: `High`
* **Date Added**: 2026-11-05
* **Date Completed**: 2026-11-05
* **Documents to Update Upon Completion**:
  - [`docs/MARKDOWN_SYNC_SPEC.md`](MARKDOWN_SYNC_SPEC.md) (Self-contained `docs/seed-trips/` paths and `yy-mm-[trip name].md` naming)
  - [`docs/DATA_MODEL.md`](DATA_MODEL.md) (Verification of canonical relational models)
  - [`AGENTS.md`](../AGENTS.md) (Zero external folder dependency, authentic 9 seed trips)
  - [`docs/livingUserStoriesAndAcceptanceCriteria.md`](livingUserStoriesAndAcceptanceCriteria.md) (US-SYNC-01 updated criteria)
* **Context**:
  Previously, markdown synchronization had an external coupling to `settings.BASE_DIR.parent / 'Trips'`, violating repo self-containment. Additionally, the initial synthetic database contained outdated/non-existent trips rather than the 9 verified canonical trips from sonderring.com.
* **Objective**:
  Completely decouple the codebase from any directory outside the Git repository, provide an idempotent markdown ingestion management command, and seed the database with the verified authentic 9 trips.
* **Scope & Implementation Delivered**:
  1. **Decoupled Sync**: Updated `core/md_sync.py` so `get_trips_directory()` targets `docs/seed-trips/` inside the repository with canonical `yy-mm-[trip name].md` naming.
  2. **Management Importer**: Implemented `python manage.py import_seed_trips` with support for `--clear` and `--dir`, parsing metadata, trippers, and all items into relational models.
  3. **Zero Fabrication**: Verified all 9 trips against ground truth with all Taste and Play items strictly normalized to `Status: IDEA`.
  4. **Fixture & Baseline Parity**: Exported updated database state to `core/fixtures/seed_data.json` and unified `core/seed_initial.py`.
  5. **Sync Protection**: Added `disable_markdown_sync` context manager and deterministic tripper ordering to protect seed documents from test corruption.

### TASK-007: Change Trip View
* **ID**: `TASK-007`
* **Fix add trip text** If user has past trips, the button for new trip should just say "Add a TripSpace"
* When editing a trip, you shouldn't have the status first, it should just go to edit. 
* You need to be able to click the location and have it open on google maps in a new window

### TASK-008: Change Item Form
* **ID**: `TASK-008`
* **Change UI for the form when adding an item** 
* Default should be show more options, not show fewer options. 
* The time should be by hour only (only for stay checkin and checkout)
* For idea start and end are in fewer options, but for confirmed it should be in the main few
* Maybe add cancellation rules?
* For move, stay, and play have the length be duration
* For move you should be able to add like driving directions

### TASK-009: Item View Styling
* **ID**: `TASK-009`
* **Change View for Dimensions in tripspace**
* the item grid should span the webpage to fit it
* You should be able to click it and have a modal with all of the info