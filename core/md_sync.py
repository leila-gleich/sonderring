"""
Markdown File Synchronizer for Sonderring Trips.
Ensures that any creation, edit, status toggle, or deletion in the live web app
permanently synchronizes to the corresponding markdown file in /Trips/.
"""

import re
import os
from pathlib import Path
from django.conf import settings

TRIP_FILENAME_MAP = {
    'Malticilia 26': 'Malticilia-26.md',
    'Iceland Ring Road Expedition': 'Iceland-Ring-Road.md',
    'Iceland': 'Iceland-Ring-Road.md',
    'Norway Fjords Coastal Voyage': 'Norway-Fjords.md',
    "Joshua Tree Jan '22": 'Joshua-Tree-Jan-22.md',
    "Joshua Tree Oct '21": 'Joshua-Tree-Oct-21.md',
    'NYE 21-22': 'New-York-City-NYE-21-22.md',
    'New York City (NYE 21-22)': 'New-York-City-NYE-21-22.md',
    "California Sept. '21": 'California-Coast-Sept-21.md',
    "Utah/Vegas '21": 'Utah-Las-Vegas-21.md',
    "Colorado '21": 'Colorado-Rockies-21.md',
    "Asheville Dec '21": 'Asheville-Dec-21.md',
    'Hawaii': 'Hawaii-Islands.md',
}

_is_syncing = False


def get_trips_directory() -> Path:
    trips_dir = settings.BASE_DIR.parent / 'Trips'
    trips_dir.mkdir(parents=True, exist_ok=True)
    return trips_dir


def get_trip_filename(trip) -> str:
    if trip.title in TRIP_FILENAME_MAP:
        return TRIP_FILENAME_MAP[trip.title]
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', trip.title).strip('-')
    return f"{slug}.md" if slug else f"trip-{trip.id}.md"


def format_attribution(item) -> str:
    author = getattr(item, 'created_by', None) or getattr(item, 'recommended_by', None) or getattr(item, 'uploaded_by', None)
    editor = getattr(item, 'updated_by', None)
    author_str = f"Added by `@{author.handle}`" if author else "Added by `@traveler`"
    if editor and author and editor.id != author.id:
        return f"{author_str} · Last edited by `@{editor.handle}`"
    return f"{author_str} · Last edited by `@{author.handle}`" if author else author_str


def format_stay(stay) -> list[str]:
    lines = [f"* **{stay.title}**"]
    if stay.place_type:
        lines.append(f"  * **Place Type**: {stay.place_type}")
    
    cap_parts = []
    if stay.num_beds:
        cap_parts.append(f"{stay.num_beds} Bed{'s' if stay.num_beds > 1 else ''}")
    if stay.num_rooms:
        cap_parts.append(f"{stay.num_rooms} Room{'s' if stay.num_rooms > 1 else ''}")
    if stay.num_guests:
        cap_parts.append(f"{stay.num_guests} Guest{'s' if stay.num_guests > 1 else ''}")
    if cap_parts:
        lines.append(f"  * **Capacity**: {' · '.join(cap_parts)}")
    
    if stay.address:
        lines.append(f"  * **Address**: {stay.address}")
    
    if stay.check_in and stay.check_out:
        in_str = stay.check_in.strftime('%b %d, %Y, %g:%M %p')
        out_str = stay.check_out.strftime('%b %d, %Y, %g:%M %p')
        lines.append(f"  * **Dates**: {in_str} – {out_str}")
    elif stay.check_in:
        lines.append(f"  * **Check-in**: {stay.check_in.strftime('%b %d, %Y')}")
    
    if stay.total_price is not None:
        lines.append(f"  * **Total Price**: ${stay.total_price:,.2f} {stay.currency}")
    
    if stay.booking_link:
        lines.append(f"  * **Booking Link**: {stay.booking_link}")
    
    code = stay.confirmation_code
    if code:
        lines.append(f"  * **Confirmation Code**: `{code}` (Encrypted AES-256)")
    
    # Vault attachments
    attachment = stay.attachments.first()
    if attachment:
        lines.append(f"  * **Vault Attachment**: `{attachment.file_name}`")
    
    if stay.notes:
        lines.append(f"  * **Notes**: {stay.notes}")
    
    lines.append(f"  * **Attribution**: {format_attribution(stay)}")
    return lines


def format_nav(nav) -> list[str]:
    lines = [f"* **{nav.title}**"]
    lines.append(f"  * **Mode**: {nav.mode}")
    stage_disp = nav.get_trip_stage_display() if hasattr(nav, 'get_trip_stage_display') else nav.trip_stage
    lines.append(f"  * **Trip Stage**: `{nav.trip_stage}` ({stage_disp})")
    lines.append(f"  * **Direction**: `{nav.direction}`")
    
    if nav.origin_address:
        lines.append(f"  * **Origin Address**: {nav.origin_address}")
    if nav.destination_address:
        lines.append(f"  * **Destination Address**: {nav.destination_address}")
    
    if nav.departure_time and nav.arrival_time:
        dep_str = nav.departure_time.strftime('%b %d, %Y, %g:%M %p')
        arr_str = nav.arrival_time.strftime('%b %d, %Y, %g:%M %p')
        lines.append(f"  * **Schedule**: {dep_str} ➔ {arr_str}")
    elif nav.departure_time:
        lines.append(f"  * **Departure**: {nav.departure_time.strftime('%b %d, %Y, %g:%M %p')}")
    
    lines.append(f"  * **Confidence**: Date: `{nav.date_confidence}` · Time: `{nav.time_confidence}`")
    
    if nav.flexibility_notes:
        lines.append(f"  * **Flexibility Notes**: {nav.flexibility_notes}")
    
    if nav.price is not None:
        lines.append(f"  * **Price**: ${nav.price:,.2f} {nav.currency}")
    
    if nav.passenger_name:
        lines.append(f"  * **Passengers**: {nav.passenger_name}")
    
    if nav.booking_link:
        lines.append(f"  * **Booking Link**: {nav.booking_link}")
    
    code = nav.confirmation_code
    if code:
        lines.append(f"  * **Confirmation Code**: `{code}` (Encrypted AES-256)")
    
    attachment = nav.attachments.first()
    if attachment:
        lines.append(f"  * **Vault Attachment**: `{attachment.file_name}`")
    
    lines.append(f"  * **Attribution**: {format_attribution(nav)}")
    return lines


def format_do(do) -> list[str]:
    lines = [f"* **{do.title}**"]
    if do.activity_type:
        lines.append(f"  * **Activity Type**: {do.activity_type}")
    if do.address:
        lines.append(f"  * **Address / Venue**: {do.address}")
    
    if do.start_time and do.end_time:
        st_str = do.start_time.strftime('%b %d, %g:%M %p')
        et_str = do.end_time.strftime('%g:%M %p')
        lines.append(f"  * **Schedule**: {st_str} – {et_str}")
    elif do.start_time:
        lines.append(f"  * **Schedule**: {do.start_time.strftime('%b %d, %g:%M %p')}")
    
    if do.price is not None:
        lines.append(f"  * **Price**: ${do.price:,.2f} {do.currency}" if do.price > 0 else "$0.00 USD (Free admission)")
    
    code = do.confirmation_code
    if code:
        lines.append(f"  * **Confirmation Code**: `{code}` (Encrypted AES-256)")
    
    if do.description:
        lines.append(f"  * **Description**: {do.description}")
    
    if do.link:
        lines.append(f"  * **Link**: {do.link}")
    
    lines.append(f"  * **Attribution**: {format_attribution(do)}")
    return lines


def format_rec(rec) -> list[str]:
    lines = [f"* **{rec.title}**"]
    lines.append(f"  * **Category**: {rec.get_category_display() if hasattr(rec, 'get_category_display') else rec.category}")
    if rec.address:
        lines.append(f"  * **Address / Venue**: {rec.address}")
    if rec.link:
        lines.append(f"  * **Link**: {rec.link}")
    if rec.description:
        lines.append(f"  * **Description**: {rec.description}")
    lines.append(f"  * **Attribution**: {format_attribution(rec)}")
    return lines


def sync_trip_to_markdown(trip):
    """
    Renders the Trip and all related Stays, Navs, Dos, and Recs into a standardized markdown file
    in /Trips/, conforming strictly to the required schema headers and subheaders.
    """
    global _is_syncing
    if _is_syncing:
        return
    
    _is_syncing = True
    try:
        trips_dir = get_trips_directory()
        filename = get_trip_filename(trip)
        filepath = trips_dir / filename

        lines = []
        lines.append(f"# {trip.title}\n")
        lines.append("## Trip Metadata")
        lines.append(f"* **Trip Title**: {trip.title}")
        lines.append(f"* **Location**: {trip.location}")
        lines.append(f"* **Time Granularity**: `{trip.time_granularity}`")
        lines.append(f"* **Dates**: {trip.formatted_dates}")
        
        status_map = {
            'IDEA': 'Idea (Tentative)',
            'CONFIRMED': 'Confirmed',
            'COMPLETE': 'Complete',
        }
        status_str = status_map.get(trip.status, trip.get_status_display() if hasattr(trip, 'get_status_display') else trip.status)
        lines.append(f"* **Status**: `{trip.status}` ({status_str})")

        creator = trip.created_by
        creator_name = creator.full_name if creator else "Traveler"
        creator_handle = creator.handle if creator else "traveler"
        lines.append(f"* **Owner (`created_by`)**: `@{creator_handle}` ({creator_name})")

        lines.append("* **Trippers (`trip_members`)**:")
        members = trip.members.select_related('user').all()
        if members:
            for m in members:
                role_label = m.get_role_display() if hasattr(m, 'get_role_display') else m.role
                lines.append(f"  * `@{m.user.handle}` — {role_label}")
        else:
            lines.append(f"  * `@{creator_handle}` — Owner")

        if trip.description:
            lines.append(f"* **Description**: {trip.description}")

        lines.append("\n---\n")

        # ==========================================
        # 1. STAYS
        # ==========================================
        lines.append("## Stays\n")
        confirmed_stays = list(trip.stays.filter(status='CONFIRMED').order_by('created_at'))
        potential_stays = list(trip.stays.filter(status='IDEA').order_by('created_at'))

        lines.append("### Confirmed")
        if confirmed_stays:
            for stay in confirmed_stays:
                lines.extend(format_stay(stay))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Potential")
        if potential_stays:
            for stay in potential_stays:
                lines.extend(format_stay(stay))
        else:
            lines.append("*None recorded.*")

        lines.append("\n---\n")

        # ==========================================
        # 2. NAVS
        # ==========================================
        lines.append("## Navs\n")
        confirmed_navs = list(trip.navs.filter(status='CONFIRMED').order_by('created_at'))
        potential_navs = list(trip.navs.filter(status='IDEA').order_by('created_at'))

        lines.append("### Confirmed")
        if confirmed_navs:
            for nav in confirmed_navs:
                lines.extend(format_nav(nav))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Potential")
        if potential_navs:
            for nav in potential_navs:
                lines.extend(format_nav(nav))
        else:
            lines.append("*None recorded.*")

        lines.append("\n---\n")

        # ==========================================
        # 3. DOS (Strictly separated from Recs)
        # ==========================================
        lines.append("## Dos\n")
        confirmed_dos = list(trip.dos.filter(status='CONFIRMED').order_by('created_at'))
        potential_dos = list(trip.dos.filter(status='IDEA').order_by('created_at'))

        lines.append("### Confirmed")
        if confirmed_dos:
            for do in confirmed_dos:
                lines.extend(format_do(do))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Potential")
        if potential_dos:
            for do in potential_dos:
                lines.extend(format_do(do))
        else:
            lines.append("*None recorded.*")

        lines.append("\n---\n")

        # ==========================================
        # 4. RECS (Strictly separated from Dos)
        # ==========================================
        lines.append("## Recs\n")
        confirmed_recs = list(trip.recs.filter(status='CONFIRMED').order_by('created_at'))
        potential_recs = list(trip.recs.filter(status='IDEA').order_by('created_at'))

        lines.append("### Confirmed")
        if confirmed_recs:
            for rec in confirmed_recs:
                lines.extend(format_rec(rec))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Potential")
        if potential_recs:
            for rec in potential_recs:
                lines.extend(format_rec(rec))
        else:
            lines.append("*None recorded.*")

        content = "\n".join(lines) + "\n"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        try:
            update_readme_catalog()
        except Exception:
            pass

    finally:
        _is_syncing = False


def update_readme_catalog():
    """Refreshes the markdown table of contents in Trips/README.md based on current trips in the DB."""
    from .models import Trip
    trips_dir = get_trips_directory()
    readme_path = trips_dir / 'README.md'
    
    trips = Trip.objects.all().order_by('created_at')
    rows = []
    for idx, t in enumerate(trips, 1):
        filename = get_trip_filename(t)
        status_label = t.get_status_display() if hasattr(t, 'get_status_display') else t.status
        rows.append(f"| {idx} | **{t.title}** | {t.location} | `{t.status}` ({status_label}) | {t.formatted_dates} (`{t.time_granularity}`) | [`{filename}`]({filename}) |")
    
    table_content = "\n".join(rows)
    
    readme_text = f"""# Sonderring Canonical Trips Archive (`Trips/`)

This directory contains local markdown representations of the canonical trips developed for **Sonderring**, mirroring the planning archives on Google Drive and matching the active database models in `Sonderringv0`.

---

## 📁 Trip Documents Catalog

| # | Trip Name | Destination | Status | Dates / Granularity | File Link |
| :-: | :--- | :--- | :---: | :--- | :--- |
{table_content}

---

## 🏗️ Structural Uniformity Rules

Every markdown file in this folder strictly conforms to the canonical template:
1. **Trip Metadata Header**: Title, Location, Time Granularity, Dates, Status, Owner (`created_by`), Trippers (`trip_members`), and Description.
2. **`## Stays`**:
   * `### Confirmed`
   * `### Potential`
3. **`## Navs`**:
   * `### Confirmed`
   * `### Potential`
4. **`## Dos`** *(Strictly separated from Recs)*:
   * `### Confirmed`
   * `### Potential`
5. **`## Recs`** *(Strictly separated from Dos)*:
   * `### Confirmed`
   * `### Potential`

---

## 📊 Comprehensive Schema Evaluation

To read the in-depth comparative analysis, identified limitations in the current database schema, and actionable recommendations for improvement, see:
👉 **[`SCHEMA_EVALUATION.md`](SCHEMA_EVALUATION.md)**
"""
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_text)


def delete_trip_markdown(trip):
    """Removes the trip markdown file when a trip is deleted from the database."""
    trips_dir = get_trips_directory()
    filename = get_trip_filename(trip)
    filepath = trips_dir / filename
    if filepath.exists():
        filepath.unlink()
    try:
        update_readme_catalog()
    except Exception:
        pass
