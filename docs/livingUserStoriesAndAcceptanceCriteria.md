# Living User Stories & Acceptance Criteria

> **Document Status**: Canonical & Living  
> **Last Updated**: 2026-10-31  
> **Traceability & Source Documents**:  
> • [`docs/PRD.md`](file:///Users/leilagleich/Desktop/sonderring/docs/PRD.md) (Product Requirements Document)  
> • [`docs/MVP.md`](file:///Users/leilagleich/Desktop/sonderring/docs/MVP.md) (MVP Scope & Roadmap)  
> • [`docs/CYBERSECURITY.md`](file:///Users/leilagleich/Desktop/sonderring/docs/CYBERSECURITY.md) (Security Architecture & Threat Model)  
> • [`docs/PAGE_OUTLINE.md`](file:///Users/leilagleich/Desktop/sonderring/docs/PAGE_OUTLINE.md) (Site Architecture & UI Flows)  
> • [`docs/DATA_MODEL.md`](file:///Users/leilagleich/Desktop/sonderring/docs/DATA_MODEL.md) (Canonical Data Model & Schema)  
> • [`docs/API_SPECIFICATION.md`](file:///Users/leilagleich/Desktop/sonderring/docs/API_SPECIFICATION.md) (REST API Contract)  
> • [`docs/MARKDOWN_SYNC_SPEC.md`](file:///Users/leilagleich/Desktop/sonderring/docs/MARKDOWN_SYNC_SPEC.md) (Markdown Sync Spec)  
> • [`docs/tripItemAttributesReference.md`](file:///Users/leilagleich/Desktop/sonderring/docs/tripItemAttributesReference.md)  
> • [`AGENTS.md`](file:///Users/leilagleich/Desktop/sonderring/AGENTS.md) (Domain Nomenclature)  
> • [`README.md`](file:///Users/leilagleich/Desktop/sonderring/README.md)  
> • [`Trips/README.md`](file:///Users/leilagleich/Desktop/Trips/README.md)  

---

## 📋 Document Maintenance Protocol

1. **Continuous Synchronization**: Whenever changes, additions, or deprecations are made to specifications, form guidelines, schema models, or reference documents (such as `docs/tripItemAttributesReference.md` or `AGENTS.md`), this document **must immediately be updated** to maintain parity.
2. **Nomenclature Compliance**: All stories, acceptance criteria, and technical references must adhere strictly to the [TripSpace Nomenclature Architecture](file:///Users/leilagleich/Desktop/sonderring/AGENTS.md#L1-L101) (TripSpace $\rightarrow$ Dimension $\rightarrow$ Item $\rightarrow$ Category, Input vs. Attribute, Readiness States: `IDEA`, `CONFIRMED`, `COMPLETE`).
3. **Traceability**: Every story must link back to its originating specification requirement and verify both frontend (Item Input) and backend (Item Attribute) behavioral criteria.

---

## 🗺️ Epic Index

- [Epic 1: TripSpace Management & Metadata (US-TS)](#epic-1-tripspace-management--metadata)
- [Epic 2: Dimension Architecture & Unified Structure (US-DIM)](#epic-2-dimension-architecture--unified-structure)
- [Epic 3: Item Status-First Creation & Workflow (US-FLOW)](#epic-3-item-status-first-creation--workflow)
- [Epic 4: Move Dimension Items (US-MOVE)](#epic-4-move-dimension-items)
- [Epic 5: Stay Dimension Items (US-STAY)](#epic-5-stay-dimension-items)
- [Epic 6: Taste Dimension Items (US-TASTE)](#epic-6-taste-dimension-items)
- [Epic 7: Play Dimension Items (US-PLAY)](#epic-7-play-dimension-items)
- [Epic 8: Security, Field Encryption & Document Vault (US-SEC)](#epic-8-security-field-encryption--document-vault)
- [Epic 9: Bidirectional Markdown Synchronization (US-SYNC)](#epic-9-bidirectional-markdown-synchronization)

---

## Epic 1: TripSpace Management & Metadata

### US-TS-01: Create and View TripSpaces
**As a** traveler,  
**I want to** create a new TripSpace with core destination and timing metadata,  
**So that** I have a dedicated, structured collaborative canvas for my trip.

#### Acceptance Criteria
- **AC-TS-01.1**: The user can create a TripSpace specifying:
  - **TripSpace Title** (`title`, required string)
  - **Location** (`destination`, string, e.g., "Orange County", "Iceland")
  - **Time Granularity** (`time_granularity`, dropdown selection; default: `EXACT_RANGE`; options: `EXACT_RANGE`, `MONTH`, `SEASON`, `YEAR`, `APPROXIMATE`, `DAY_COUNT`, `IDEA`)
  - **Dates** (`start_date`, `end_date`, or textual range based on granularity)
  - **Description** (`description`, text area for trip overview)
- **AC-TS-01.2**: Upon creation, the creator is assigned as Owner (`created_by`) and added to the `trip_members` list.
- **AC-TS-01.3**: TripSpace status defaults to `UPCOMING` or `IDEA` (if exact dates are unset) and can transition to `CURRENT` or `PAST`.

---

### US-TS-02: Instant Status Management on Dashboard
**As a** user browsing my trips on the dashboard,  
**I want to** update the status of a trip directly from the list view,  
**So that** I don't need to open the workspace page just to adjust trip readiness.

#### Acceptance Criteria
- **AC-TS-02.1**: Clicking the status pill or dropdown on a trip card in the dashboard updates the trip status via an inline AJAX/Fetch call.
- **AC-TS-02.2**: The interface reflects the new status immediately without requiring a full page redirect.

---

### US-TS-03: Member Collaboration & Public Recommendations
**As a** trip owner,  
**I want to** invite fellow trippers and share a public recommendation intake link,  
**So that** friends who are not on the trip can contribute ideas without gaining editing access to my itinerary.

#### Acceptance Criteria
- **AC-TS-03.1**: Trip members can be invited with specific roles (`OWNER`, `EDITOR`, `VIEWER`).
- **AC-TS-03.2**: A public recommendation link/widget allows external contributors to submit recommendations that appear in a dedicated "Recs" tab/queue.

---

## Epic 2: Dimension Architecture & Unified Structure

### US-DIM-01: Four Foundational Dimensions
**As a** traveler planning a trip,  
**I want** my itinerary partitioned into four dedicated dimensions: Move, Stay, Taste, and Play,  
**So that** every aspect of my journey is organized according to Sonderring conventions.

#### Acceptance Criteria
- **AC-DIM-01.1**: Every TripSpace displays four distinct dimension views:
  1. ✈️ **Move** — Transit, flights, rail, ferries, driving routes, car rentals.
  2. 🏨 **Stay** — Lodging, hotels, villas, campgrounds, apartments, rooms.
  3. 🍽️ **Taste** — Restaurants, cafés, street food, bars, wineries.
  4. 🎭 **Play** — Activities, tours, sights, hikes, performances, museums.
- **AC-DIM-01.2**: Every created item **must belong to exactly one dimension**. An item cannot exist unassociated with a dimension.
- **AC-DIM-01.3**: Primary dimension icons/emojis (✈️, 🏨, 🍽️, 🎭) are isolated to dimension headers and may be toggled without altering underlying item icons.
- **AC-DIM-01.4**: Each dimension view supports an optional notes/overview component at the top of the dimension container.

---

## Epic 3: Item Status-First Creation & Workflow

### US-FLOW-01: Status-First Question Flow for Modals
**As a** user clicking "Add" on any dimension (Move, Stay, Taste, Play),  
**I want to** be asked the item's status first as its own dedicated question,  
**So that** the subsequent form fields adapt to whether the item is an Idea, Confirmed reservation, or Complete memory.

#### Acceptance Criteria
- **AC-FLOW-01.1**: When opening the Add modal for any dimension, Step 1 (`item-status-step`) presents a prominent prompt:
  - *Move*: "What is the status of this transit leg?"
  - *Stay*: "What is the status of this stay?"
  - *Taste*: "What is the status of this food & drink spot?"
  - *Play*: "What is the status of this activity?"
- **AC-FLOW-01.2**: Step 1 displays three clear, selectable cards/buttons:
  - 💡 **Idea** (`IDEA`)
  - 📅 **Confirmed** (`CONFIRMED`)
  - ✅ **Complete** (`COMPLETE`)
- **AC-FLOW-01.3**: Selecting a status immediately advances the modal to Step 2 (`item-form-step`) showing the input form.
- **AC-FLOW-01.4**: Status is **not** rendered as a standard select dropdown inside the main body of the form; it is maintained via a hidden input (`input[type="hidden"][name="status"]`).
- **AC-FLOW-01.5**: Step 2 includes a persistent **Status Flow Bar** at the top showing the currently active status with a "Change Status" action that allows switching status without discarding filled inputs.

---

### US-FLOW-02: Status-Driven Readiness Rules
**As a** user filling out an item form,  
**I want** validation and field requirements to match the selected readiness state,  
**So that** I am not blocked by mandatory dates when brainstorming ideas, but prompted for required details when booking is confirmed.

#### Acceptance Criteria
- **AC-FLOW-02.1**: **`IDEA` State**:
  - Dates and times are strictly **optional**.
  - Submit button indicates idea capture (e.g., "Save Transit Idea", "Save Stay Idea", "Save Taste Idea", "Save Activity Idea").
- **AC-FLOW-02.2**: **`CONFIRMED` State**:
  - For **Move**, **Taste**, and **Play**: A single `date` is **mandatory**; time is optional. Required indicator (`*`) is displayed.
  - For **Stay**: Both `check_in` (Start Date) and `check_out` (End Date) are **mandatory**; times are optional.
  - Submit button indicates confirmation (e.g., "Save Confirmed Stay", "Save Confirmed Transit").
- **AC-FLOW-02.3**: **`COMPLETE` State**:
  - Archived past item; dates remain valid.
- **AC-FLOW-02.4**: Base inputs required for all items regardless of dimension:
  - **Name*** (title, required)
  - **Status*** (selected via status flow, required)
  - **Type** (dimension-specific dropdown)
  - **Link** (optional URL)
  - **Notes / Description** (optional text area)

---

## Epic 4: Move Dimension Items

### US-MOVE-01: Move Item Inputs & Attributes
**As a** traveler,  
**I want to** record transportation legs (flights, trains, driving routes, car rentals),  
**So that** my travel logistics are clearly scheduled.

#### Acceptance Criteria
- **AC-MOVE-01.1**: **Primary Inputs** (displayed immediately in Step 2):
  - **Name\*** (`title`, text input, required)
  - **Status\*** (`status`, hidden input preset by Step 1, required)
  - **Type** (`mode`, dropdown; options: `Planes`, `Trains`, `Car`)
  - **Origin** (`origin`, text input)
  - **Destination** (`destination`, text input)
  - **Link** (`booking_link`, URL input)
  - **Notes** (`notes` / `description`, text area)
- **AC-MOVE-01.2**: **Expandable "More Options" Section**:
  - Toggled via a dedicated "More Options" button (`#btnToggleMoveMoreOptions`).
  - **Departure Date** (`departure_date`, date input; required if status is `CONFIRMED`).
  - **Departure Time** (`departure_time`, time input; optional, enabled for Planes and Trains).
  - **Company** (`company`, text input, e.g., "Delta Airlines", "Hertz").
  - **Price** (`cost`, float/decimal input, e.g., `249.50`).
  - **Confirmation Code** (`confirmation_code`, text input; encrypted at rest).
  - **Upload Documents** (`documents`, file input; supporting PDF, PNG, JPG).
- **AC-MOVE-01.3**: For Planes and Trains, departure time input is prominently accessible alongside the departure date.

---

## Epic 5: Stay Dimension Items

### US-STAY-01: Stay Item Inputs & Attributes
**As a** traveler,  
**I want to** record accommodations and lodging details,  
**So that** my group has clear check-in, check-out, and duration information.

#### Acceptance Criteria
- **AC-STAY-01.1**: **Primary Inputs** (displayed immediately in Step 2):
  - **Name\*** (`title`, text input, required)
  - **Status\*** (`status`, hidden input preset by Step 1, required)
  - **Type** (`place_type`, dropdown; options: `Hotel`, `Home`, `Apartment`, `Room`, `Bed`)
  - **Location** (`address`, text input)
  - **Link** (`booking_link`, URL input)
  - **Notes** (`description`, text area)
- **AC-STAY-01.2**: **Expandable "More Options" Section**:
  - Toggled via a dedicated "More Options" button (`#btnToggleStayMoreOptions`).
  - **Stay Length** (`stay_length`, integer input, e.g., `3`) paired with **Unit Selector** (`stay_length_unit`, dropdown; options: `Day(s)`, `Week(s)`, `Month(s)`).
  - **Start Date** (`check_in`, date input; required if status is `CONFIRMED`).
  - **End Date** (`check_out`, date input; required if status is `CONFIRMED`).
  - **Price** (`total_price`, float/decimal input, e.g., `450.00`).
  - **Confirmation Code** (`confirmation_code`, text input; encrypted at rest).
  - **Upload Documents** (`documents`, file input).
- **AC-STAY-01.3**: Chronological validation ensures `check_out` cannot precede `check_in`.
- **AC-STAY-01.4**: Check-in time (`check_in_time`) and check-out time (`check_out_time`) are optional.

---

## Epic 6: Taste Dimension Items

### US-TASTE-01: Taste Item Inputs & Dynamic Categorization
**As a** foodie traveler,  
**I want to** catalog dining spots and bars with specific cuisines and drink categories,  
**So that** our dining options are well-organized and easy to decide upon.

#### Acceptance Criteria
- **AC-TASTE-01.1**: **Primary Inputs** (displayed immediately in Step 2):
  - **Name\*** (`title`, text input, required)
  - **Status\*** (`status`, hidden input preset by Step 1, required)
  - **Type** (`taste_type`, dropdown; options: `Food`, `Drink`)
  - **Location** (`address` / venue, text input)
  - **Link** (`booking_link` / menu link, URL input)
  - **Notes** (`description`, text area)
- **AC-TASTE-01.2**: **Conditional Categorization based on Type**:
  - **If Type is `Food`**: Renders **Cuisine** dropdown (`cuisine`; options: `American`, `African`, `Asian`, `Contemporary`, `European`, `Fusion`, `Indian`, `Mediterranean`, `Mexican`, `South American`).
  - **If Type is `Drink`**: Renders **Category** dropdown (`drink_category`; options: `Beer`, `Cocktails`, `Wine`, `Tea & Coffee`, `Juice and Smoothies`, `Other`).
- **AC-TASTE-01.3**: **Expandable "More Options" Section**:
  - Toggled via "More Options" button (`#btnToggleTasteMoreOptions`).
  - **Price Range**: Interactive button selector (`$`, `$$`, `$$$`, `$$$$`).
  - **Date** (`date`, date input; required only if status is `CONFIRMED`, optional if `IDEA`).
  - **Booking Reference** (`confirmation_code`, text input; encrypted at rest).
  - **Upload Documents** (`documents`, file input).
- **AC-TASTE-01.4**: **Schema Invariant**: Taste items **do not have an end date or end time** attribute.

---

## Epic 7: Play Dimension Items

### US-PLAY-01: Play Item Inputs & Attributes
**As a** traveler,  
**I want to** schedule activities, tours, and sightseeing spots,  
**So that** daily adventures and outings are organized.

#### Acceptance Criteria
- **AC-PLAY-01.1**: **Primary Inputs** (displayed immediately in Step 2):
  - **Name\*** (`title`, text input, required)
  - **Status\*** (`status`, hidden input preset by Step 1, required)
  - **Type** (`play_type`, dropdown; options: `Outdoors`, `Tours`, `Events`, `Sightseeing`, `Other`)
  - **Location** (`address` / landmark, text input)
  - **Link** (`booking_link` / ticket URL, URL input)
  - **Notes** (`description`, text area)
- **AC-PLAY-01.2**: **Expandable "More Options" Section**:
  - Toggled via "More Options" button (`#btnTogglePlayMoreOptions`).
  - **Price**: Interactive button selector (`Free`, `$`, `$$`, `$$$`, `$$$$`).
  - **Date** (`date`, date input; required only if status is `CONFIRMED`, optional if `IDEA`).
  - **Time** (`time`, time input, optional).
  - **Confirmation Code** (`confirmation_code`, text input; encrypted at rest).
  - **Upload Documents** (`documents`, file input).
- **AC-PLAY-01.3**: For Play items categorized as a **Tour**, an optional `length` / duration attribute is supported.

---

## Epic 8: Security, Field Encryption & Document Vault

### US-SEC-01: Application-Level Field Encryption
**As a** security-conscious traveler,  
**I want** my confirmation numbers, booking codes, and keypad entries encrypted at the application layer,  
**So that** sensitive travel credentials are never stored in plaintext in the database or logs.

#### Acceptance Criteria
- **AC-SEC-01.1**: All confirmation codes (`_encrypted_confirmation_code`) across Move, Stay, Taste, and Play are encrypted using **AES-256-GCM** prior to persistence.
- **AC-SEC-01.2**: Stay keypad codes and sensitive check-in notes (`notes`) utilize encrypted text fields (`EncryptedTextField`) with Associated Authenticated Data (AAD).
- **AC-SEC-01.3**: Decryption occurs only in memory when rendering views for authenticated members of the TripSpace.

---

### US-SEC-02: Secure Document Vault
**As a** user uploading travel confirmation PDFs and boarding passes,  
**I want** uploaded files safely stored with obfuscated storage paths,  
**So that** unauthenticated users cannot guess document URLs.

#### Acceptance Criteria
- **AC-SEC-02.1**: Uploaded documents are saved under `media/vault/YYYY/MM/<uuid>.<ext>`.
- **AC-SEC-02.2**: Download endpoints require active user authentication and trip membership verification.

---

## Epic 9: Bidirectional Markdown Synchronization

### US-SYNC-01: Markdown File and Fixture Parity
**As a** developer or offline traveler,  
**I want** trip markdown files in `Trips/*.md` to mirror the database state in real-time,  
**So that** changes in either the web interface or text files stay completely synchronized.

#### Acceptance Criteria
- **AC-SYNC-01.1**: Every markdown file follows the strict section ordering:
  1. Trip Metadata Header (Title, Location, Time Granularity, Dates, Status, Owner, Trippers, Description)
  2. `## Move` (`### Confirmed`, `### Potential`, `### Complete`)
  3. `## Stay` (`### Confirmed`, `### Potential`, `### Complete`)
  4. `## Taste` (`### Confirmed`, `### Potential`, `### Complete`)
  5. `## Play` (`### Confirmed`, `### Potential`, `### Complete`)
- **AC-SYNC-01.2**: Database saves automatically emit markdown updates, and file updates trigger synchronization hooks.

---

## 📊 Traceability Matrix

| Epic / Story ID | Dimension | Scope | Reference Document Section | Primary Template / Code Location |
| :--- | :--- | :--- | :--- | :--- |
| **US-TS-01** | Global | Full Stack | `PRD.md` § 4.1, `tripItemAttributesReference.md` § 1 | [`core/models.py`](file:///Users/leilagleich/Desktop/sonderring/core/models.py#L90), `templates/trip_workspace.html` |
| **US-TS-02** | Global | UI / View | `PRD.md` § 4.1, `PAGE_OUTLINE.md` § 2.1 | `core/views.py`, `templates/home.html` |
| **US-TS-03** | Global | Collaboration | `PRD.md` § 4.1, `PAGE_OUTLINE.md` § 2.3 | `core/models.py`, `templates/trip_workspace.html` |
| **US-DIM-01** | All | Full Stack | `AGENTS.md` § 1.2, `PRD.md` § 4.3 | `templates/trip_workspace.html` |
| **US-FLOW-01**| All | Frontend | `PRD.md` § 4.2, `PAGE_OUTLINE.md` § 3 | `templates/trip_workspace.html#L1400-L2400` |
| **US-FLOW-02**| All | Full Stack | `AGENTS.md` § 3, `DATA_MODEL.md` § 3 | `core/forms.py`, `core/views.py`, `templates/trip_workspace.html` |
| **US-MOVE-01**| Move | Full Stack | `tripItemAttributesReference.md` § 3.1, `DATA_MODEL.md` § 2.4 | [`core/models.py`](file:///Users/leilagleich/Desktop/sonderring/core/models.py#L250), `templates/trip_workspace.html` |
| **US-STAY-01**| Stay | Full Stack | `tripItemAttributesReference.md` § 3.2, `DATA_MODEL.md` § 2.5 | [`core/models.py`](file:///Users/leilagleich/Desktop/sonderring/core/models.py#L380), `templates/trip_workspace.html` |
| **US-TASTE-01**| Taste | Full Stack | `tripItemAttributesReference.md` § 3.3, `DATA_MODEL.md` § 2.6 | [`core/models.py`](file:///Users/leilagleich/Desktop/sonderring/core/models.py#L520), `templates/trip_workspace.html` |
| **US-PLAY-01**| Play | Full Stack | `tripItemAttributesReference.md` § 3.4, `DATA_MODEL.md` § 2.7 | [`core/models.py`](file:///Users/leilagleich/Desktop/sonderring/core/models.py#L650), `templates/trip_workspace.html` |
| **US-SEC-01** | All | Security | `CYBERSECURITY.md` § 2, `README.md` § Security | `core/fields.py`, `core/encryption.py` |
| **US-SEC-02** | All | Vault | `CYBERSECURITY.md` § 4, `DATA_MODEL.md` § 2.8 | `core/views.py`, `media/vault/` |
| **US-SYNC-01**| All | Data / Tooling| `MARKDOWN_SYNC_SPEC.md` § 2-4, `Trips/README.md` | `core/fixture_sync.py`, `core/signals.py` |
