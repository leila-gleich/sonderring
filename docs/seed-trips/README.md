# Sonderring Canonical Trips Archive (`docs/seed-trips/`)

This directory contains local markdown representations of the canonical trips developed for **Sonderring**, completely self-contained within the Git repository and matching the active database models.

---

## 📁 Trip Documents Catalog

| # | Trip Name | Destination | Status | Dates / Granularity | File Link |
| :-: | :--- | :--- | :---: | :--- | :--- |
| 1 | **The Flame July '21** | St. George, UT & Las Vegas, NV | `PAST` (Past) | Jul 01 – 08, 2021 (`EXACT_RANGE`) | [`21-07-Flame.md`](21-07-Flame.md) |
| 2 | **Joshua Tree Oct '21** | Joshua Tree, CA | `PAST` (Past) | October 2021 (`MONTH`) | [`21-10-JT.md`](21-10-JT.md) |
| 3 | **Asheville Dec '21** | Asheville, NC | `PAST` (Past) | Dec 07 – 11, 2021 (`EXACT_RANGE`) | [`21-12-Asheville.md`](21-12-Asheville.md) |
| 4 | **NYE '21-'22** | San Diego, CA | `PAST` (Past) | Dec 30, 2021 – Jan 02, 2022 (`EXACT_RANGE`) | [`21-12-NYE.md`](21-12-NYE.md) |
| 5 | **Joshua Tree Jan '22** | Twentynine Palms, CA | `PAST` (Past) | Jan 10 – 13, 2022 (`EXACT_RANGE`) | [`22-01-JT.md`](22-01-JT.md) |
| 6 | **Hawaii '26** | Big Island & Kauai, HI | `PAST` (Past) | Aug 02 – 10, 2026 (`EXACT_RANGE`) | [`26-08-Hawaii.md`](26-08-Hawaii.md) |
| 7 | **Malticilia '26** | Malta & Sicily (Taormina, Syracuse) | `PAST` (Past) | Sep 06 – 17, 2026 (`EXACT_RANGE`) | [`26-09-Malticilia.md`](26-09-Malticilia.md) |
| 8 | **Halloween Staycation '26** | Orange County, CA | `PAST` (Past) | Oct 30 – Nov 02, 2026 (`EXACT_RANGE`) | [`26-10-Halloween-Staycation.md`](26-10-Halloween-Staycation.md) |
| 9 | **Iceland '26** | Golden Circle & Reykjavik, Iceland | `PAST` (Past) | Oct 13 – 22, 2026 (`EXACT_RANGE`) | [`26-10-Iceland.md`](26-10-Iceland.md) |
| 10 | **Japan** | Japan | `UPCOMING` (Upcoming) | Nov 13 – 26, 2026 (`EXACT_RANGE`) | [`Japan.md`](Japan.md) |

---

## 🏗️ Structural Uniformity Rules (Move, Stay, Taste, Play)

Every markdown file in this folder strictly conforms to the canonical template in exact order:
1. **Trip Metadata Header**: Title, Location, Time Granularity, Dates, Status, Owner (`created_by`), Trippers (`trip_members`), and Description.
2. **`## Move`**: Transit, flights, trains, road trips, car rentals, ferries.
   * `### Confirmed`
   * `### Potential`
   * `### Complete`
3. **`## Stay`**: Lodging, accommodations, hotel rooms, cabins, Airbnbs.
   * `### Confirmed`
   * `### Potential`
   * `### Complete`
4. **`## Taste`**: Food and drink, restaurants, bars, cafés, wineries, food markets, food tours.
   * `### Confirmed`
   * `### Potential`
   * `### Complete`
5. **`## Play`**: Activities, sightseeing, hikes, tours, experiences, sports, attractions, tips.
   * `### Confirmed`
   * `### Potential`
   * `### Complete`

---

## 📊 Comprehensive Schema Evaluation

To read the in-depth comparative analysis, identified limitations in the current database schema, and actionable recommendations for improvement, see:
👉 **[`SCHEMA_EVALUATION.md`](SCHEMA_EVALUATION.md)**
