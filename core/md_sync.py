"""
Markdown File Synchronizer for Sonderring Trips.
Ensures that any creation, edit, status toggle, or deletion in the live web app
permanently synchronizes to the corresponding markdown file in /Trips/.
Organized into four canonical elements in exact order: Move, Stay, Taste, Play.
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
    guest = getattr(item, 'guest_name', None)
    author = getattr(item, 'created_by', None) or getattr(item, 'recommended_by', None) or getattr(item, 'uploaded_by', None)
    editor = getattr(item, 'updated_by', None)
    
    if guest:
        author_str = f"Recommended by **{guest}** (via Guest Link)"
    elif author:
        author_str = f"Added by `@{author.handle}`"
    else:
        author_str = "Added by `@traveler`"
        
    if editor and author and editor.id != author.id:
        return f"{author_str} · Last edited by `@{editor.handle}`"
    return f"{author_str} · Last edited by `@{author.handle}`" if (author and not guest) else author_str


def format_move(move) -> list[str]:
    lines = [f"* **{move.title}**"]
    lines.append(f"  * **Mode**: {move.mode}")
    stage_disp = move.get_trip_stage_display() if hasattr(move, 'get_trip_stage_display') else move.trip_stage
    lines.append(f"  * **Trip Stage**: `{move.trip_stage}` ({stage_disp})")
    lines.append(f"  * **Direction**: `{move.direction}`")
    
    if move.origin_address:
        lines.append(f"  * **Origin Address**: {move.origin_address}")
    if move.destination_address:
        lines.append(f"  * **Destination Address**: {move.destination_address}")
    
    if move.departure_time:
        if move.is_departure_time_set:
            lines.append(f"  * **Departure**: {move.departure_time.strftime('%b %d, %Y, %I:%M %p')}")
        else:
            lines.append(f"  * **Departure**: {move.departure_time.strftime('%b %d, %Y')}")
    
    lines.append(f"  * **Confidence**: Date: `{move.date_confidence}` · Time: `{move.time_confidence}`")
    
    if move.flexibility_notes:
        lines.append(f"  * **Flexibility Notes**: {move.flexibility_notes}")
    
    if move.price is not None:
        lines.append(f"  * **Price**: ${move.price:,.2f} {move.currency}")
    
    if move.passenger_name:
        lines.append(f"  * **Passengers**: {move.passenger_name}")
    
    if move.booking_link:
        lines.append(f"  * **Booking Link**: {move.booking_link}")
    
    code = move.confirmation_code
    if code:
        lines.append(f"  * **Confirmation Code**: `{code}` (Encrypted AES-256)")
    
    attachment = move.attachments.first()
    if attachment:
        lines.append(f"  * **Vault Attachment**: `{attachment.file_name}`")
    
    lines.append(f"  * **Attribution**: {format_attribution(move)}")
    return lines


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
        if stay.is_check_in_time_set and stay.is_check_out_time_set:
            in_str = stay.check_in.strftime('%b %d, %Y, %I:%M %p')
            out_str = stay.check_out.strftime('%b %d, %Y, %I:%M %p')
        elif stay.is_check_in_time_set:
            in_str = stay.check_in.strftime('%b %d, %Y, %I:%M %p')
            out_str = stay.check_out.strftime('%b %d, %Y')
        elif stay.is_check_out_time_set:
            in_str = stay.check_in.strftime('%b %d, %Y')
            out_str = stay.check_out.strftime('%b %d, %Y, %I:%M %p')
        else:
            in_str = stay.check_in.strftime('%b %d, %Y')
            out_str = stay.check_out.strftime('%b %d, %Y')
        lines.append(f"  * **Dates**: {in_str} – {out_str}")
    elif stay.check_in:
        if stay.is_check_in_time_set:
            lines.append(f"  * **Check-in**: {stay.check_in.strftime('%b %d, %Y, %I:%M %p')}")
        else:
            lines.append(f"  * **Check-in**: {stay.check_in.strftime('%b %d, %Y')}")
    
    if stay.total_price is not None:
        lines.append(f"  * **Total Price**: ${stay.total_price:,.2f} {stay.currency}")
    
    if stay.booking_link:
        lines.append(f"  * **Booking Link**: {stay.booking_link}")
    
    code = stay.confirmation_code
    if code:
        lines.append(f"  * **Confirmation Code**: `{code}` (Encrypted AES-256)")
    
    attachment = stay.attachments.first()
    if attachment:
        lines.append(f"  * **Vault Attachment**: `{attachment.file_name}`")
    
    if stay.notes:
        lines.append(f"  * **Notes**: {stay.notes}")
    
    lines.append(f"  * **Attribution**: {format_attribution(stay)}")
    return lines


def format_taste(taste) -> list[str]:
    lines = [f"* **{taste.title}**"]
    taste_label = taste.get_taste_type_display() if hasattr(taste, 'get_taste_type_display') else taste.taste_type
    lines.append(f"  * **Taste Type**: {taste_label}")
    
    if taste.address:
        lines.append(f"  * **Address / Venue**: {taste.address}")
    
    if taste.start_time:
        if taste.is_start_time_set:
            lines.append(f"  * **Schedule**: {taste.start_time.strftime('%b %d, %I:%M %p')}")
        else:
            lines.append(f"  * **Date**: {taste.start_time.strftime('%b %d, %Y')}")
    
    if taste.price is not None:
        lines.append(f"  * **Price**: ${taste.price:,.2f} {taste.currency}" if taste.price > 0 else "  * **Price**: $0.00 USD (Complimentary)")
    
    code = taste.confirmation_code
    if code:
        lines.append(f"  * **Confirmation Code**: `{code}` (Encrypted AES-256)")
    
    if taste.description:
        lines.append(f"  * **Description**: {taste.description}")
        
    if taste.notes:
        lines.append(f"  * **Notes**: {taste.notes}")
    
    if taste.link:
        lines.append(f"  * **Link**: {taste.link}")
        
    attachment = taste.attachments.first()
    if attachment:
        lines.append(f"  * **Vault Attachment**: `{attachment.file_name}`")
    
    lines.append(f"  * **Attribution**: {format_attribution(taste)}")
    return lines


def format_play(play) -> list[str]:
    lines = [f"* **{play.title}**"]
    play_label = play.get_play_type_display() if hasattr(play, 'get_play_type_display') else play.play_type
    lines.append(f"  * **Play Type**: {play_label}")
    
    if play.address:
        lines.append(f"  * **Address / Venue**: {play.address}")
    
    if play.start_time:
        if play.is_start_time_set:
            lines.append(f"  * **Schedule**: {play.start_time.strftime('%b %d, %I:%M %p')}")
        else:
            lines.append(f"  * **Date**: {play.start_time.strftime('%b %d, %Y')}")
    
    if play.price is not None:
        lines.append(f"  * **Price**: ${play.price:,.2f} {play.currency}" if play.price > 0 else "  * **Price**: $0.00 USD (Free admission)")
    
    code = play.confirmation_code
    if code:
        lines.append(f"  * **Confirmation Code**: `{code}` (Encrypted AES-256)")
    
    if play.description:
        lines.append(f"  * **Description**: {play.description}")
        
    if play.notes:
        lines.append(f"  * **Notes**: {play.notes}")
    
    if play.link:
        lines.append(f"  * **Link**: {play.link}")
        
    attachment = play.attachments.first()
    if attachment:
        lines.append(f"  * **Vault Attachment**: `{attachment.file_name}`")
    
    lines.append(f"  * **Attribution**: {format_attribution(play)}")
    return lines


def sync_trip_to_markdown(trip):
    """
    Renders the Trip and all related Move, Stay, Taste, Play items into a standardized markdown file
    in /Trips/, strictly in the exact order: Move, Stay, Taste, Play.
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
            'UPCOMING': 'Upcoming',
            'CURRENT': 'Current',
            'PAST': 'Past',
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
        # 1. MOVE (Transit, Flights, Drives, Ferries)
        # ==========================================
        lines.append("## Move\n")
        confirmed_moves = list(trip.moves.filter(status='CONFIRMED').order_by('departure_time', 'created_at'))
        potential_moves = list(trip.moves.filter(status='IDEA').order_by('departure_time', 'created_at'))
        complete_moves = list(trip.moves.filter(status='COMPLETE').order_by('departure_time', 'created_at'))

        lines.append("### Confirmed")
        if confirmed_moves:
            for move in confirmed_moves:
                lines.extend(format_move(move))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Potential")
        if potential_moves:
            for move in potential_moves:
                lines.extend(format_move(move))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Complete")
        if complete_moves:
            for move in complete_moves:
                lines.extend(format_move(move))
        else:
            lines.append("*None recorded.*")

        lines.append("\n---\n")

        # ==========================================
        # 2. STAY (Accommodations & Lodging)
        # ==========================================
        lines.append("## Stay\n")
        confirmed_stays = list(trip.stays.filter(status='CONFIRMED').order_by('check_in', 'created_at'))
        potential_stays = list(trip.stays.filter(status='IDEA').order_by('check_in', 'created_at'))
        complete_stays = list(trip.stays.filter(status='COMPLETE').order_by('check_in', 'created_at'))

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

        lines.append("\n### Complete")
        if complete_stays:
            for stay in complete_stays:
                lines.extend(format_stay(stay))
        else:
            lines.append("*None recorded.*")

        lines.append("\n---\n")

        # ==========================================
        # 3. TASTE (Food, Drink, Dining, Bars)
        # ==========================================
        lines.append("## Taste\n")
        confirmed_tastes = list(trip.tastes.filter(status='CONFIRMED').order_by('start_time', 'created_at'))
        potential_tastes = list(trip.tastes.filter(status='IDEA').order_by('start_time', 'created_at'))
        complete_tastes = list(trip.tastes.filter(status='COMPLETE').order_by('start_time', 'created_at'))

        lines.append("### Confirmed")
        if confirmed_tastes:
            for taste in confirmed_tastes:
                lines.extend(format_taste(taste))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Potential")
        if potential_tastes:
            for taste in potential_tastes:
                lines.extend(format_taste(taste))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Complete")
        if complete_tastes:
            for taste in complete_tastes:
                lines.extend(format_taste(taste))
        else:
            lines.append("*None recorded.*")

        lines.append("\n---\n")

        # ==========================================
        # 4. PLAY (Activities, Sights, Experiences, Tips)
        # ==========================================
        lines.append("## Play\n")
        confirmed_plays = list(trip.plays.filter(status='CONFIRMED').order_by('start_time', 'created_at'))
        potential_plays = list(trip.plays.filter(status='IDEA').order_by('start_time', 'created_at'))
        complete_plays = list(trip.plays.filter(status='COMPLETE').order_by('start_time', 'created_at'))

        lines.append("### Confirmed")
        if confirmed_plays:
            for play in confirmed_plays:
                lines.extend(format_play(play))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Potential")
        if potential_plays:
            for play in potential_plays:
                lines.extend(format_play(play))
        else:
            lines.append("*None recorded.*")

        lines.append("\n### Complete")
        if complete_plays:
            for play in complete_plays:
                lines.extend(format_play(play))
        else:
            lines.append("*None recorded.*")

        content = "\n".join(lines) + "\n"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        try:
            update_readme_catalog()
        except Exception:
            pass

        return filepath

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
