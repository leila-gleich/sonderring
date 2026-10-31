# Trip Item Attributes & Input Guidelines — Sonderring

> **Document Status**: Canonical Reference  
> **Nomenclature Conformance**: [`AGENTS.md`](file:///Users/leilagleich/Desktop/sonderring/AGENTS.md)  
> **Related Specifications**: [`docs/livingUserStoriesAndAcceptanceCriteria.md`](file:///Users/leilagleich/Desktop/sonderring/docs/livingUserStoriesAndAcceptanceCriteria.md) · [`docs/DATA_MODEL.md`](file:///Users/leilagleich/Desktop/sonderring/docs/DATA_MODEL.md) · [`docs/PAGE_OUTLINE.md`](file:///Users/leilagleich/Desktop/sonderring/docs/PAGE_OUTLINE.md)

---

## 1. TripSpace Metadata

- **TripSpace Title**: Required display name (e.g., *Iceland 26*, *Malticilia 26*).
- **Location**: Destination city, region, or country.
- **Time Granularity**: Dropdown selection (Default: `EXACT_RANGE`; options: `EXACT_RANGE`, `MONTH`, `SEASON`, `YEAR`, `APPROXIMATE`, `DAY_COUNT`, `IDEA`).
- **Dates**: Start date and end date for exact ranges.
- **Status**: Current readiness (`UPCOMING`, `CURRENT`, `PAST`).
- **Owner (`created_by`)**: User profile of creator.
- **Trippers (`trip_members`)**: List of participating members and roles (`OWNER`, `EDITOR`, `VIEWER`).
- **Description**: Text overview of the trip.

---

## 2. Universal Item Input Rules

### 2.1. Status-First Question Flow
When adding or editing any item across all four dimensions, the modal presents **Status Selection as Step 1**:
- Prompts user to select: **Idea** (`IDEA`), **Confirmed** (`CONFIRMED`), or **Complete** (`COMPLETE`).
- Transitions to Step 2 with the appropriate input form tailored to that status.

### 2.2. Universal Base Inputs
Every item across all dimensions displays these initial primary inputs:
- **Name\*** (Required string)
- **Status\*** (Preset by Step 1)
- **Type** (Dimension-specific dropdown)
- **Web Link** (Optional URL)
- **Notes / Description** (Text area)
- **Expandable "More Options" Toggle**: Contains secondary details, encrypted confirmation codes / booking references, and document uploads.

---

## 3. Dimension-Specific Item Inputs

### 3.1. Move Dimension Items ✈️

#### Primary Inputs (Step 2 Initial View):
- **Name\*** (Title, required)
- **Status\*** (Hidden input from Step 1)
- **Type** (Dropdown: `Planes`, `Trains`, `Car`)
- **Origin** (Text input)
- **Destination** (Text input)
- **Link** (Booking / check-in URL)
- **Notes** (Text area)

#### Expand for "More Options":
- **Departure Date** (Date input; mandatory if status is `CONFIRMED`)
- **Departure Time** (Time input; prominently displayed for `Planes` and `Trains`)
- **Company** (Carrier name, e.g., *Delta Airlines*, *Hertz*)
- **Price** (Decimal / Float input)
- **Confirmation Code** (Text input; encrypted with AES-256-GCM)
- **Upload Documents** (File attachment: tickets, boarding passes)

---

### 3.2. Stay Dimension Items 🏨

#### Primary Inputs (Step 2 Initial View):
- **Name\*** (Title, required)
- **Status\*** (Hidden input from Step 1)
- **Type** (Dropdown: `Hotel`, `Home`, `Apartment`, `Room`, `Bed`)
- **Location** (Address text input)
- **Link** (Booking URL)
- **Notes** (Text area for general house rules)

#### Expand for "More Options":
- **Stay Length** (Integer input, e.g., `3`) paired with Unit Selector (`Day(s)`, `Week(s)`, `Month(s)`)
- **Start Date** (Check-in date; mandatory if status is `CONFIRMED`)
- **End Date** (Check-out date; mandatory if status is `CONFIRMED`, must occur after Start Date)
- **Price** (Decimal / Float input)
- **Confirmation Code** (Text input; encrypted with AES-256-GCM)
- **Upload Documents** (Hotel vouchers, lease agreements)

---

### 3.3. Taste Dimension Items 🍽️

#### Primary Inputs (Step 2 Initial View):
- **Name\*** (Title, required)
- **Status\*** (Hidden input from Step 1)
- **Type** (Dropdown: `Food`, `Drink`)
- **Location** (Address / venue text input)
- **Link** (Menu or reservation URL)
- **Notes** (Text area)

#### Dynamic Categorization & Expand for "More Options":
- **If Type is Food**:
  - **Cuisine**: Dropdown (`American`, `African`, `Asian`, `Contemporary`, `European`, `Fusion`, `Indian`, `Mediterranean`, `Mexican`, `South American`)
- **If Type is Drink**:
  - **Category**: Dropdown (`Beer`, `Cocktails`, `Wine`, `Tea & Coffee`, `Juice and Smoothies`, `Other`)
- **For Both Types**:
  - **Price**: Button selector (`$`, `$$`, `$$$`, `$$$$`)
  - **Date**: Date input (Mandatory if `CONFIRMED`, optional if `IDEA`)
  - **Booking Reference**: Text input (Encrypted with AES-256-GCM)
  - **Upload Documents** (Menu PDFs, booking receipts)

> **Core Invariant**: Taste items **do not possess an end date or end time**.

---

### 3.4. Play Dimension Items 🎭

#### Primary Inputs (Step 2 Initial View):
- **Name\*** (Title, required)
- **Status\*** (Hidden input from Step 1)
- **Type** (Dropdown: `Outdoors`, `Tours`, `Events`, `Sightseeing`, `Other`)
- **Location** (Address / venue text input)
- **Link** (Guide or booking URL)
- **Notes** (Text area)

#### Expand for "More Options":
- **Price**: Button selector (`Free`, `$`, `$$`, `$$$`, `$$$$`)
- **Date**: Date input (Mandatory if `CONFIRMED`, optional if `IDEA`)
- **Time**: Time input (Optional)
- **Confirmation Code**: Text input (Encrypted with AES-256-GCM)
- **Upload Documents** (Event tickets, tour itineraries)
- **Tour Duration**: For Play items categorized as a **Tour**, users have the option to specify `length` / duration.
