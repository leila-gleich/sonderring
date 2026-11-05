# Language-Agnostic API Contract Specification — Sonderring

> **Document Status**: Canonical & Living  
> **Version**: 1.0.0  
> **Protocol**: RESTful HTTP / JSON  
> **Implementation Target**: Framework & Language Agnostic  

---

## 1. Global API Conventions

### 1.1. Base URL & Versioning
All API endpoints follow semantic versioning under the `/api/v1` namespace:
$$\text{Base URL} = \texttt{https://<host>/api/v1}$$

### 1.2. Authentication & Authorization
- **Browser Clients**: Cookie-based session authentication with CSRF tokens (`X-CSRFToken` header).
- **Mobile / External Clients**: Bearer tokens (`Authorization: Bearer <jwt_or_api_token>`).
- **Object-Level Authorization**: Every endpoint scoped under `/trips/{trip_id}/` strictly validates that the authenticated identity is a member of `trip.trip_members`.

### 1.3. Standard Error Envelope (RFC 7807 Compliant)
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Stay check-out date must occur after check-in date.",
    "field_errors": {
      "check_out": ["Must be after check_in"]
    },
    "timestamp": "2026-10-31T20:00:00Z"
  }
}
```

---

## 2. TripSpace Endpoints

### 2.1. List User Trips
`GET /api/v1/trips`
- **Response**: `200 OK`
```json
{
  "trips": [
    {
      "id": "7b8d4f61-2e38-4e89-91a3-ef081d428901",
      "title": "Iceland 26",
      "destination": "Reykjavik & Ring Road",
      "time_granularity": "EXACT_RANGE",
      "start_date": "2026-10-13",
      "end_date": "2026-10-26",
      "status": "UPCOMING",
      "role": "OWNER",
      "member_count": 3
    }
  ]
}
```

### 2.2. Create TripSpace
`POST /api/v1/trips`
- **Request Body**:
```json
{
  "title": "Iceland 26",
  "destination": "Iceland",
  "time_granularity": "EXACT_RANGE",
  "start_date": "2026-10-13",
  "end_date": "2026-10-26",
  "status": "UPCOMING",
  "description": "Two week Ring Road exploration."
}
```
- **Response**: `201 Created`

### 2.3. Inline Status Quick-Update
`PATCH /api/v1/trips/{trip_id}/status`
- **Request Body**:
```json
{
  "status": "CURRENT"
}
```
- **Response**: `200 OK` (Returns updated status and timestamp).

---

## 3. Dimension Item Endpoints (Move, Stay, Taste, Play)

### 3.1. Create Move Item
`POST /api/v1/trips/{trip_id}/move`
- **Request Body**:
```json
{
  "title": "Flight to Reykjavik",
  "status": "CONFIRMED",
  "mode": "Planes",
  "origin": "LAX",
  "destination": "KEF",
  "departure_date": "2026-10-13",
  "departure_time": "15:25",
  "carrier": "Delta Airlines",
  "cost": 845.20,
  "confirmation_code": "GH9L7T",
  "booking_link": "https://delta.com",
  "notes": "Terminal 2, seats 14A/14B"
}
```
- **Security Processing**: The application encrypts `confirmation_code` with AES-256-GCM before writing to storage.
- **Response**: `201 Created` (Returns item UUID, masked/decrypted code for authorized member).

---

### 3.2. Create Stay Item
`POST /api/v1/trips/{trip_id}/stay`
- **Request Body**:
```json
{
  "title": "Hotel Grímsborgir",
  "status": "CONFIRMED",
  "place_type": "Hotel",
  "address": "Asborgir 30, Selfoss, 801, Iceland",
  "stay_length": 3,
  "stay_length_unit": "Day(s)",
  "check_in": "2026-10-14",
  "check_out": "2026-10-17",
  "total_price": 950.00,
  "confirmation_code": "HG-984210",
  "notes": "Door keypad PIN: 4829 (Lockbox on east porch)"
}
```
- **Security Processing**: `confirmation_code` and door notes in `notes` are encrypted with AES-256-GCM using AAD context `stay:<uuid>`.
- **Response**: `201 Created`

---

### 3.3. Create Taste Item
`POST /api/v1/trips/{trip_id}/taste`
- **Request Body (Food)**:
```json
{
  "title": "Kol Restaurant",
  "status": "CONFIRMED",
  "taste_type": "Food",
  "cuisine": "Contemporary",
  "address": "Skólavörðustígur 40, 101 Reykjavík",
  "price_tier": "$$$",
  "date": "2026-10-15",
  "time": "19:30",
  "booking_reference": "KOL-7712",
  "booking_link": "https://kolrestaurant.is",
  "notes": "Tasting menu reserved for 3 people"
}
```
- **Response**: `201 Created`

---

### 3.4. Create Play Item
`POST /api/v1/trips/{trip_id}/play`
- **Request Body (Tour)**:
```json
{
  "title": "Inside the Volcano Tour",
  "status": "CONFIRMED",
  "play_type": "Tours",
  "tour_length": "4 Hours",
  "address": "Thrihnukagigur Volcano Base Camp",
  "price_tier": "$$$$",
  "date": "2026-10-16",
  "time": "10:00",
  "confirmation_code": "VOLC-883921",
  "booking_link": "https://insidethevolcano.com",
  "notes": "Bring waterproof hiking boots and warm layers"
}
```
- **Response**: `201 Created`

---

## 4. Document Vault Endpoints

### 4.1. Upload Document
`POST /api/v1/trips/{trip_id}/vault/upload`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Binary file stream (`.pdf`, `.png`, `.jpg`).
  - `item_type`: String (`"move"`, `"stay"`, `"taste"`, `"play"`).
  - `item_id`: Target item UUID.
- **Response**: `201 Created`
```json
{
  "document_id": "f5e4d3c2-b1a0-9876-5432-10fedcba9876",
  "original_name": "boarding_pass_kef.pdf",
  "file_size": 245890,
  "download_url": "/api/v1/trips/7b8d4f61-2e38-4e89-91a3-ef081d428901/vault/f5e4d3c2-b1a0-9876-5432-10fedcba9876"
}
```

### 4.2. Download Document Stream
`GET /api/v1/trips/{trip_id}/vault/{document_id}`
- **Security Check**: Verifies session and trip membership.
- **Headers**:
  - `Content-Type`: `application/pdf`
  - `Content-Disposition`: `attachment; filename="boarding_pass_kef.pdf"`
  - `Cache-Control`: `private, no-cache, no-store, must-revalidate`
- **Response**: `200 OK` (Binary Stream)

---

## 5. Public Recommendation Intake Endpoint

`POST /api/v1/public/recommendations/{invite_token}`
- **Auth**: None required (Token-authenticated).
- **Request Body**:
```json
{
  "recommender_name": "Sarah",
  "title": "Braud & Co Bakery",
  "dimension": "Taste",
  "category": "Bakery / Breakfast",
  "address_or_link": "Frakkastigur 16, Reykjavik",
  "notes": "Get the hot cinnamon roll straight out of the oven!"
}
```
- **Response**: `201 Created` (Item placed in TripSpace Recs queue).
