import re
from decimal import Decimal
from pathlib import Path
from datetime import datetime, date, time

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from core.models import UserProfile, Trip, TripMember, Move, Stay, Taste, Play
from core.md_sync import disable_markdown_sync


MONTH_NAMES = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9, 'oct': 10,
    'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
}

KNOWN_USERS = {
    'leila': {'email': 'leila@sonderring.com', 'full_name': 'Leila Gleich', 'phone': '+1-310-555-0192'},
    'tiffany': {'email': 'tiffany@sonderring.com', 'full_name': 'Tiffany', 'phone': '+1-513-555-0120'},
    'liz': {'email': 'liz@sonderring.com', 'full_name': 'Liz', 'phone': '+1-619-555-0182'},
    'catherine': {'email': 'catherine@sonderring.com', 'full_name': 'Catherine', 'phone': '+1-760-555-0143'},
    'edo': {'email': 'edo@sonderring.com', 'full_name': 'Edo', 'phone': '+1-310-555-0158'},
    'lindsey': {'email': 'lindsey@sonderring.com', 'full_name': 'Lindsey', 'phone': '+1-702-555-0191'},
    'tara': {'email': 'tara@sonderring.com', 'full_name': 'Tara', 'phone': '+1-702-555-0177'},
    'dad': {'email': 'dad@sonderring.com', 'full_name': 'Dad', 'phone': '+1-808-555-0134'},
    'samt': {'email': 'sam@sonderring.com', 'full_name': 'Sam Taylor', 'phone': '+1-415-555-0144'},
    'alexm': {'email': 'alex@sonderring.com', 'full_name': 'Alex Morgan', 'phone': '+1-212-555-0188'},
    'jordanl': {'email': 'jordan@sonderring.com', 'full_name': 'Jordan Lee', 'phone': '+1-646-555-0163'},
}


def get_or_create_user(handle: str, full_name: str = None) -> UserProfile:
    handle = handle.lower().lstrip('@')
    info = KNOWN_USERS.get(handle, {})
    email = info.get('email', f"{handle}@sonderring.com")
    name = full_name or info.get('full_name', handle.capitalize())
    phone = info.get('phone', None)
    user, created = UserProfile.objects.get_or_create(
        email=email,
        defaults={
            'handle': handle,
            'full_name': name,
            'phone_number': phone,
        }
    )
    if not user.has_usable_password():
        user.set_password('Sonderring2026!')
        user.save()
    return user


def clean_val(val: str) -> str:
    val = val.strip()
    if val.startswith('`') and val.endswith('`'):
        val = val[1:-1].strip()
    return val


def parse_time(time_str: str):
    if not time_str:
        return None
    time_str = time_str.strip().lower()
    m = re.match(r'(\d+):(\d+)\s*(am|pm)?', time_str)
    if m:
        hr = int(m.group(1))
        mn = int(m.group(2))
        ampm = m.group(3)
        if ampm == 'pm' and hr < 12:
            hr += 12
        elif ampm == 'am' and hr == 12:
            hr = 0
        return time(hr, mn)
    return None


def parse_date(date_str: str):
    if not date_str:
        return None
    date_str = date_str.strip()
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', date_str)
    if m:
        mo = int(m.group(1))
        day = int(m.group(2))
        yr = int(m.group(3))
        if yr < 100:
            yr += 2000
        return date(yr, mo, day)
    return None


def parse_trip_dates(dates_str):
    dates_str = dates_str.strip()
    # 1. Month D1, YYYY1 – Month D2, YYYY2
    m = re.match(r'^([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})\s*[-–—]\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})$', dates_str)
    if m:
        m1 = MONTH_NAMES[m.group(1).lower()]
        d1 = int(m.group(2))
        y1 = int(m.group(3))
        m2 = MONTH_NAMES[m.group(4).lower()]
        d2 = int(m.group(5))
        y2 = int(m.group(6))
        return date(y1, m1, d1), date(y2, m2, d2), y1, m1, m2

    # 2. Month1 D1 – Month2 D2, YYYY
    m = re.match(r'^([A-Za-z]+)\s+(\d{1,2})\s*[-–—]\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})$', dates_str)
    if m:
        m1 = MONTH_NAMES[m.group(1).lower()]
        d1 = int(m.group(2))
        m2 = MONTH_NAMES[m.group(3).lower()]
        d2 = int(m.group(4))
        yr = int(m.group(5))
        return date(yr, m1, d1), date(yr, m2, d2), yr, m1, m2

    # 3. Month D1 – D2, YYYY
    m = re.match(r'^([A-Za-z]+)\s+(\d{1,2})\s*[-–—]\s*(\d{1,2}),?\s*(\d{4})$', dates_str)
    if m:
        mo = MONTH_NAMES[m.group(1).lower()]
        d1 = int(m.group(2))
        d2 = int(m.group(3))
        yr = int(m.group(4))
        return date(yr, mo, d1), date(yr, mo, d2), yr, mo, mo

    # 4. Month YYYY
    m = re.match(r'^([A-Za-z]+)\s+(\d{4})$', dates_str)
    if m:
        mo = MONTH_NAMES[m.group(1).lower()]
        yr = int(m.group(2))
        return None, None, yr, mo, mo

    return None, None, 2026, None, None


def parse_md_file(filepath: Path):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    lines = text.splitlines()
    doc = {
        'title': '',
        'metadata': {},
        'move': [],
        'stay': [],
        'taste': [],
        'play': [],
    }

    current_section = None
    current_item = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        if stripped.startswith('# ') and not doc['title']:
            doc['title'] = stripped[2:].strip()
            continue

        if stripped.lower().startswith('## trip metadata'):
            current_section = 'metadata'
            current_item = None
            continue
        elif stripped.lower().startswith('## move'):
            current_section = 'move'
            current_item = None
            continue
        elif stripped.lower().startswith('## stay'):
            current_section = 'stay'
            current_item = None
            continue
        elif stripped.lower().startswith('## taste'):
            current_section = 'taste'
            current_item = None
            continue
        elif stripped.lower().startswith('## play'):
            current_section = 'play'
            current_item = None
            continue
        elif stripped.startswith('## '):
            current_section = None
            current_item = None
            continue

        if current_section == 'metadata':
            m = re.match(r'^\*\s+\*\*([^*]+)\*\*:\s*(.*)$', stripped)
            if m:
                key = m.group(1).split('(')[0].strip()
                val = m.group(2).strip()
                doc['metadata'][key] = clean_val(val)
            elif stripped.startswith('* ') and '—' in stripped:
                doc['metadata'].setdefault('trippers', []).append(stripped[2:].strip())
            continue

        if current_section in ('move', 'stay', 'taste', 'play'):
            if stripped == '*None recorded.*':
                continue
            item_match = re.match(r'^\*\s+(?:Name:\s+|\*\*)([^*]+)(?:\*\*)?$', stripped)
            if item_match and not stripped.startswith('  '):
                name = item_match.group(1).strip()
                current_item = {'name': name}
                doc[current_section].append(current_item)
                continue
            
            prop_match = re.match(r'^\*\s+(?:\*\*)?([^*:]+)(?:\*\*)?:\s*(.*)$', stripped)
            if prop_match and current_item is not None:
                prop_key = prop_match.group(1).strip()
                prop_val = clean_val(prop_match.group(2))
                current_item[prop_key] = prop_val

    return doc


class Command(BaseCommand):
    help = 'Imports canonical seed trip markdown files from docs/seed-trips/ into the relational database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clears existing trips from database before importing canonical seed trips.'
        )
        parser.add_argument(
            '--dir',
            type=str,
            default=None,
            help='Optional custom directory path to seed trips markdown files.'
        )

    def handle(self, *args, **options):
        with disable_markdown_sync():
            trips_dir_opt = options.get('dir')
            if trips_dir_opt:
                trips_dir = Path(trips_dir_opt)
            else:
                trips_dir = settings.BASE_DIR / 'docs' / 'seed-trips'

            if not trips_dir.exists():
                self.stderr.write(self.style.ERROR(f"Directory {trips_dir} does not exist."))
                return

            if options.get('clear'):
                self.stdout.write("Clearing existing trips from database...")
                Trip.objects.all().delete()

            imported_trips = []

            for md_file in sorted(trips_dir.glob('*.md')):
                if md_file.name == 'README.md':
                    continue

                self.stdout.write(f"Parsing {md_file.name}...")
                doc = parse_md_file(md_file)
                meta = doc['metadata']

                title = meta.get('Trip Title') or doc['title']
                location = meta.get('Location', '')
                time_granularity = meta.get('Time Granularity', 'EXACT_RANGE')
                status = meta.get('Status', 'PAST')
                description = meta.get('Description', f"Trip to {location}")

                dates_str = meta.get('Dates', '')
                s_date, e_date, yr, s_m, e_m = parse_trip_dates(dates_str)

                owner_raw = meta.get('Owner', '@leila')
                owner_handle = 'leila'
                owner_name = 'Leila Gleich'
                m_owner = re.match(r'`?@([a-zA-Z0-9_]+)`?(?:\s*\((.*)\))?', owner_raw)
                if m_owner:
                    owner_handle = m_owner.group(1)
                    if m_owner.group(2):
                        owner_name = m_owner.group(2)
                owner = get_or_create_user(owner_handle, owner_name)

                trip, created = Trip.objects.get_or_create(
                    title=title,
                    defaults={
                        'location': location,
                        'time_granularity': time_granularity,
                        'status': status,
                        'description': description,
                        'start_date': s_date,
                        'end_date': e_date,
                        'year': yr,
                        'start_month': s_m,
                        'end_month': e_m,
                        'created_by': owner,
                    }
                )
                if not created:
                    trip.location = location
                    trip.time_granularity = time_granularity
                    trip.status = status
                    trip.description = description
                    trip.start_date = s_date
                    trip.end_date = e_date
                    trip.year = yr
                    trip.start_month = s_m
                    trip.end_month = e_m
                    trip.created_by = owner
                    trip.save()

                # Trip Members
                TripMember.objects.get_or_create(trip=trip, user=owner, defaults={'role': 'OWNER'})
                for t_line in meta.get('trippers', []):
                    m_trip = re.match(r'`?@([a-zA-Z0-9_]+)`?\s*—\s*(.*)', t_line)
                    if m_trip:
                        m_handle = m_trip.group(1)
                        m_role_str = m_trip.group(2).strip().upper()
                        m_user = get_or_create_user(m_handle)
                        role = 'EDITOR'
                        if 'OWNER' in m_role_str:
                            role = 'OWNER'
                        elif 'VIEWER' in m_role_str:
                            role = 'VIEWER'
                        TripMember.objects.get_or_create(trip=trip, user=m_user, defaults={'role': role})

                # Clear existing items for this trip
                trip.moves.all().delete()
                trip.stays.all().delete()
                trip.tastes.all().delete()
                trip.plays.all().delete()

                # 1. Moves
                for m_item in doc['move']:
                    m_title = m_item.get('name', 'Move Item')
                    m_status = m_item.get('Status', 'CONFIRMED')
                    m_date_str = m_item.get('Date', '')
                    d = parse_date(m_date_str)
                    t_dept = parse_time(m_item.get('Departure Time', ''))
                    t_arr = parse_time(m_item.get('Arrival Time', ''))

                    dept_dt = None
                    has_dept = False
                    if d and t_dept:
                        dept_dt = timezone.make_aware(datetime.combine(d, t_dept))
                        has_dept = True
                    elif d:
                        dept_dt = timezone.make_aware(datetime.combine(d, time(0, 0)))
                        has_dept = False

                    arr_dt = None
                    has_arr = False
                    if d and t_arr:
                        arr_dt = timezone.make_aware(datetime.combine(d, t_arr))
                        has_arr = True
                    elif d:
                        arr_dt = timezone.make_aware(datetime.combine(d, time(0, 0)))
                        has_arr = False

                    text_corpus = f"{m_title} {m_item.get('Notes', '')} {m_item.get('Flight', '')}".lower()
                    if any(k in text_corpus for k in ['flight', 'dl ', 'km ', 'ua ', 'as ', 'airline', 'lax', 'avl', 'san', 'dtw', 'koa', 'lih', 'las', 'cvg', 'kef', 'mla', 'cta']):
                        mode = 'Planes'
                    elif any(k in text_corpus for k in ['train', 'rail', 'trenitalia']):
                        mode = 'Trains'
                    elif any(k in text_corpus for k in ['ferry', 'boat']):
                        mode = 'Ferry'
                    elif any(k in text_corpus for k in ['car', 'drive', 'rental', 'hertz', 'road trip']):
                        mode = 'Car'
                    else:
                        mode = 'Planes'

                    company = m_item.get('Flight') or ''
                    if not company:
                        for comp in ['Delta', 'Alaska Airlines', 'KM Malta', 'United', 'Hertz', 'Trenitalia']:
                            if comp.lower() in text_corpus:
                                company = comp
                                break

                    move = Move(
                        trip=trip,
                        title=m_title,
                        status=m_status,
                        mode=mode,
                        company=company,
                        origin_address=m_item.get('Origin', ''),
                        destination_address=m_item.get('Destination', ''),
                        departure_time=dept_dt,
                        has_departure_time=has_dept,
                        arrival_time=arr_dt,
                        has_arrival_time=has_arr,
                        flexibility_notes=m_item.get('Notes', ''),
                        description=m_item.get('Description', ''),
                        created_by=owner
                    )
                    code = m_item.get('Confirmation/Reference') or m_item.get('Confirmation Code')
                    if code:
                        move.confirmation_code = code
                    move.save()

                # 2. Stays
                for s_item in doc['stay']:
                    s_title = s_item.get('name', 'Stay Item')
                    s_status = s_item.get('Status', 'CONFIRMED')
                    s_d_str = s_item.get('Start Date', '')
                    e_d_str = s_item.get('End Date', '')
                    s_d = parse_date(s_d_str)
                    e_d = parse_date(e_d_str)

                    check_in = timezone.make_aware(datetime.combine(s_d, time(15, 0))) if s_d else None
                    check_out = timezone.make_aware(datetime.combine(e_d, time(11, 0))) if e_d else None

                    s_text = f"{s_title} {s_item.get('Notes', '')}".lower()
                    if any(k in s_text for k in ['hotel', 'resort', 'inn', 'suites', 'lodge']):
                        place_type = 'Hotel'
                    elif any(k in s_text for k in ['house', 'retreat', 'home', 'oasis', 'airbnb', 'cabin']):
                        place_type = 'Home'
                    elif 'apartment' in s_text:
                        place_type = 'Apartment'
                    else:
                        place_type = 'Hotel'

                    stay = Stay(
                        trip=trip,
                        title=s_title,
                        status=s_status,
                        place_type=place_type,
                        address=s_item.get('Location', ''),
                        check_in=check_in,
                        check_out=check_out,
                        has_check_in_time=False,
                        has_check_out_time=False,
                        notes=s_item.get('Notes', ''),
                        description=s_item.get('Description', ''),
                        created_by=owner
                    )
                    code = s_item.get('Confirmation/Reference') or s_item.get('Confirmation Code')
                    if code:
                        stay.confirmation_code = code
                    p_val = s_item.get('Price')
                    if p_val and re.match(r'^\$?\d+(\.\d+)?$', p_val):
                        stay.total_price = Decimal(p_val.lstrip('$'))
                    stay.save()

                # 3. Tastes (strictly IDEA per canonical directive)
                for t_item in doc['taste']:
                    t_title = t_item.get('name', 'Taste Item')
                    t_status = 'IDEA'
                    t_text = f"{t_title} {t_item.get('Description', '')} {t_item.get('Notes', '')}".lower()
                    if any(k in t_text for k in ['bar', 'beer', 'brewery', 'cocktail', 'wine', 'cafe', 'coffee']):
                        taste_type = 'Drink'
                    else:
                        taste_type = 'Food'

                    taste = Taste(
                        trip=trip,
                        title=t_title,
                        status=t_status,
                        taste_type=taste_type,
                        address=t_item.get('Location', ''),
                        price_range=t_item.get('Price', '$$'),
                        description=t_item.get('Description', ''),
                        notes=t_item.get('Notes', ''),
                        created_by=owner
                    )
                    code = t_item.get('Confirmation/Reference') or t_item.get('Confirmation Code')
                    if code:
                        taste.confirmation_code = code
                    taste.save()

                # 4. Plays (strictly IDEA per canonical directive)
                for p_item in doc['play']:
                    p_title = p_item.get('name', 'Play Item')
                    p_status = 'IDEA'
                    p_text = f"{p_title} {p_item.get('Description', '')} {p_item.get('Notes', '')}".lower()
                    if any(k in p_text for k in ['tour', 'walk', 'excursion']):
                        play_type = 'Tours'
                    elif any(k in p_text for k in ['hike', 'parkway', 'forest', 'canyon', 'beach', 'sunset', 'water', 'boat', 'blue lagoon', 'fontana', 'geothermal']):
                        play_type = 'Outdoors'
                    elif any(k in p_text for k in ['concert', 'show', 'flamingosis', 'festival', 'omfg', 'desert hearts', 'party', 'nightlife', 'spin']):
                        play_type = 'Events'
                    elif any(k in p_text for k in ['museum', 'exhibit', 'art', 'statue', 'palace', 'catacombs', 'hypogeum', 'bureaucrat']):
                        play_type = 'Sightseeing'
                    else:
                        play_type = 'Sightseeing'

                    p_date = parse_date(p_item.get('Date', ''))
                    time_range = p_item.get('Time', '')
                    st_dt = None
                    end_dt = None
                    has_st = False
                    has_end = False

                    if p_date and time_range:
                        parts = re.split(r'[-–—]', time_range)
                        t1 = parse_time(parts[0]) if len(parts) > 0 else None
                        t2 = parse_time(parts[1]) if len(parts) > 1 else None
                        if t1:
                            st_dt = timezone.make_aware(datetime.combine(p_date, t1))
                            has_st = True
                        if t2:
                            end_dt = timezone.make_aware(datetime.combine(p_date, t2))
                            has_end = True
                    elif p_date:
                        st_dt = timezone.make_aware(datetime.combine(p_date, time(0, 0)))
                        has_st = False

                    price_str = p_item.get('Price', '')
                    price_tier = price_str if price_str in ['Free', '$', '$$', '$$$', '$$$$'] else '$$'
                    price_dec = Decimal('0.00') if price_tier == 'Free' else None

                    play = Play(
                        trip=trip,
                        title=p_title,
                        status=p_status,
                        play_type=play_type,
                        address=p_item.get('Location', ''),
                        price_tier=price_tier,
                        price=price_dec,
                        start_time=st_dt,
                        end_time=end_dt,
                        has_start_time=has_st,
                        has_end_time=has_end,
                        description=p_item.get('Description', ''),
                        notes=p_item.get('Notes', ''),
                        created_by=owner
                    )
                    code = p_item.get('Confirmation/Reference') or p_item.get('Confirmation Code')
                    if code:
                        play.confirmation_code = code
                    play.save()

                imported_trips.append(trip)
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Imported '{trip.title}' ({trip.status}): "
                    f"Moves={trip.moves.count()}, Stays={trip.stays.count()}, "
                    f"Tastes={trip.tastes.count()}, Plays={trip.plays.count()}"
                ))

            self.stdout.write(self.style.SUCCESS(
                f"\nSuccessfully imported all {len(imported_trips)} canonical seed trips into the database!"
            ))
