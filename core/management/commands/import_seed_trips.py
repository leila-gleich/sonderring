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

CANONICAL_USERS = {
    'leila': {'email': 'leila@sonderring.com', 'full_name': 'Leila Gleich', 'phone': '+1-310-555-0192', 'handle': 'leila'},
    'samt': {'email': 'sam@sonderring.com', 'full_name': 'Sam Taylor', 'phone': '+1-415-555-0144', 'handle': 'samt'},
    'alexm': {'email': 'alex@sonderring.com', 'full_name': 'Alex Morgan', 'phone': '+1-212-555-0188', 'handle': 'alexm'},
    'jordanl': {'email': 'jordan@sonderring.com', 'full_name': 'Jordan Lee', 'phone': '+1-646-555-0163', 'handle': 'jordanl'},
}

HANDLE_ALIAS_MAP = {
    'leila': 'leila',
    'sam': 'samt',
    'samt': 'samt',
    'alex': 'alexm',
    'alexm': 'alexm',
    'jordan': 'jordanl',
    'jordanl': 'jordanl',
}


def ensure_canonical_users(stdout=None):
    """
    Enforces that only the 4 canonical travelers exist in the database:
    Leila Gleich (@leila), Sam Taylor (@samt), Alex Morgan (@alexm), and Jordan Lee (@jordanl).
    Deletes any unauthorized or rogue accounts (e.g. gleila91, sonderring).
    """
    def log(msg):
        if stdout and hasattr(stdout, "write"):
            stdout.write(str(msg) + "\n")

    canonical_emails = {info['email'].lower() for info in CANONICAL_USERS.values()}
    # Delete any users not in canonical list
    rogue_users = UserProfile.objects.exclude(email__in=canonical_emails)
    if rogue_users.exists():
        for r_u in rogue_users:
            log(f"Removing unauthorized user: @{r_u.handle} ({r_u.email})")
            r_u.delete()

    users = {}
    for key, info in CANONICAL_USERS.items():
        user, _ = UserProfile.objects.get_or_create(
            email=info['email'],
            defaults={
                'handle': info['handle'],
                'full_name': info['full_name'],
                'phone_number': info['phone'],
                'is_active': True,
            }
        )
        if user.handle != info['handle'] or user.full_name != info['full_name']:
            user.handle = info['handle']
            user.full_name = info['full_name']
        if not user.has_usable_password():
            user.set_password('Sonderring2026!')
        user.is_active = True
        user.save()
        users[info['handle']] = user

    return users


def clean_val(val: str) -> str:
    val = val.strip()
    if val.startswith('`') and val.endswith('`'):
        val = val[1:-1].strip()
    return val


def normalize_status(val: str, default: str = 'PAST') -> str:
    if not val:
        return default
    v = clean_val(val).upper()
    if 'CURRENT' in v:
        return 'CURRENT'
    if 'UPCOMING' in v:
        return 'UPCOMING'
    if 'PAST' in v:
        return 'PAST'
    if 'IDEA' in v:
        return 'IDEA'
    if 'CONFIRMED' in v:
        return 'CONFIRMED'
    if 'COMPLETE' in v:
        return 'COMPLETE'
    return default


def normalize_granularity(val: str) -> str:
    if not val:
        return 'EXACT_RANGE'
    v = clean_val(val).upper()
    for opt in ['EXACT_RANGE', 'SEASON_YEAR', 'MONTH', 'YEAR']:
        if opt in v:
            return opt
    return 'EXACT_RANGE'


def parse_time(time_str: str):
    if not time_str:
        return None
    time_str = time_str.strip()
    m = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', time_str, re.IGNORECASE)
    if m:
        hr = int(m.group(1))
        mn = int(m.group(2))
        ampm = m.group(3).lower() if m.group(3) else None
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
    # 1. M/D/YY or MM/DD/YYYY
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', date_str)
    if m:
        mo = int(m.group(1))
        day = int(m.group(2))
        yr = int(m.group(3))
        if yr < 100:
            yr += 2000
        return date(yr, mo, day)
    # 2. Month Day, Year (e.g. Dec 08, 2021)
    m2 = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})', date_str)
    if m2 and m2.group(1).lower() in MONTH_NAMES:
        mo = MONTH_NAMES[m2.group(1).lower()]
        day = int(m2.group(2))
        yr = int(m2.group(3))
        return date(yr, mo, day)
    # 3. YYYY-MM-DD
    m3 = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if m3:
        return date(int(m3.group(1)), int(m3.group(2)), int(m3.group(3)))
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
        lines = f.readlines()

    doc = {
        'title': '',
        'metadata': {},
        'move': [],
        'stay': [],
        'taste': [],
        'play': [],
    }

    current_section = None
    current_status = 'CONFIRMED'
    current_item = None

    for raw_line in lines:
        line = raw_line.rstrip('\r\n')
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith('# ') and not doc['title']:
            doc['title'] = stripped[2:].strip()
            continue

        sec_lower = stripped.lower()
        if sec_lower.startswith('## trip metadata'):
            current_section = 'metadata'
            current_item = None
            continue
        elif sec_lower.startswith('## move'):
            current_section = 'move'
            current_status = 'CONFIRMED'
            current_item = None
            continue
        elif sec_lower.startswith('## stay'):
            current_section = 'stay'
            current_status = 'CONFIRMED'
            current_item = None
            continue
        elif sec_lower.startswith('## taste'):
            current_section = 'taste'
            current_status = 'IDEA'
            current_item = None
            continue
        elif sec_lower.startswith('## play'):
            current_section = 'play'
            current_status = 'IDEA'
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

            # Subsection headers (### Confirmed / ### Potential / ### Complete)
            if sec_lower.startswith('### confirmed'):
                current_status = 'CONFIRMED'
                current_item = None
                continue
            elif sec_lower.startswith('### potential'):
                current_status = 'IDEA'
                current_item = None
                continue
            elif sec_lower.startswith('### complete'):
                current_status = 'COMPLETE'
                current_item = None
                continue

            is_sub_bullet = line.startswith('  ') or line.startswith('\t')

            # Item header: unindented bullet
            if not is_sub_bullet and stripped.startswith('*'):
                m_bold = re.match(r'^\*\s+\*\*([^*]+)\*\*', stripped)
                if m_bold:
                    item_name = m_bold.group(1).strip()
                else:
                    item_name = re.sub(r'^\*\s+(?:Name:\s+)?', '', stripped).strip()

                current_item = {'name': item_name, 'Status': current_status}
                doc[current_section].append(current_item)
                continue

            # Item property: indented bullet
            if is_sub_bullet and current_item is not None:
                prop_match = re.match(r'^\*\s+(?:\*\*)?([^*:]+)(?:\*\*)?:\s*(.*)$', stripped)
                if prop_match:
                    prop_key = prop_match.group(1).strip()
                    prop_val = clean_val(prop_match.group(2))

                    # Normalize synonymous property keys
                    if prop_key in ('Origin Address', 'Origin'):
                        current_item['Origin'] = prop_val
                    elif prop_key in ('Destination Address', 'Destination'):
                        current_item['Destination'] = prop_val
                    elif prop_key in ('Address / Venue', 'Address', 'Location', 'Venue'):
                        current_item['Location'] = prop_val
                    elif prop_key in ('Confirmation Code', 'Confirmation/Reference', 'Booking Reference'):
                        code_clean = re.sub(r'\(.*?\)', '', prop_val).strip(' `')
                        current_item['Confirmation/Reference'] = code_clean
                    elif prop_key in ('Price Range', 'Price Tier'):
                        current_item['Price'] = prop_val
                    elif prop_key == 'Dates' and current_section == 'stay':
                        parts = re.split(r'[-–—]', prop_val)
                        if len(parts) >= 2:
                            current_item['Start Date'] = parts[0].strip()
                            current_item['End Date'] = parts[1].strip()
                        current_item['Dates'] = prop_val
                    elif prop_key == 'Departure' and current_section == 'move':
                        current_item['Departure'] = prop_val
                    elif prop_key == 'Arrival' and current_section == 'move':
                        current_item['Arrival'] = prop_val
                    elif prop_key == 'Schedule' and current_section in ('taste', 'play'):
                        current_item['Schedule'] = prop_val
                    else:
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

            # Ensure only the 4 canonical users exist
            users = ensure_canonical_users(stdout=self.stdout)
            leila_user = users['leila']

            if options.get('clear'):
                self.stdout.write("Clearing existing trips from database...")
                Trip.objects.all().delete()

            imported_trips = []

            for md_file in sorted(trips_dir.glob('*.md')):
                if md_file.name in ('README.md', 'Staycation-26.md'):
                    continue

                self.stdout.write(f"Parsing {md_file.name}...")
                doc = parse_md_file(md_file)
                meta = doc['metadata']

                title = meta.get('Trip Title') or doc['title']
                location = meta.get('Location', '')
                time_granularity = normalize_granularity(meta.get('Time Granularity', 'EXACT_RANGE'))
                status = normalize_status(meta.get('Status', 'PAST'), default='PAST')
                description = meta.get('Description', f"Trip to {location}")

                dates_str = meta.get('Dates', '')
                s_date, e_date, yr, s_m, e_m = parse_trip_dates(dates_str)

                # All seed trips are strictly associated with user @leila as creator/owner
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
                        'created_by': leila_user,
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
                    trip.created_by = leila_user
                    trip.save()

                # Trip Members: @leila is always OWNER
                TripMember.objects.get_or_create(trip=trip, user=leila_user, defaults={'role': 'OWNER'})

                # Add other canonical trippers (sam, alex, jordan) if mentioned
                for t_line in meta.get('trippers', []):
                    m_trip = re.match(r'`?@([a-zA-Z0-9_]+)`?\s*—\s*(.*)', t_line)
                    if m_trip:
                        raw_handle = m_trip.group(1).lower()
                        role_str = m_trip.group(2).strip().upper()
                        canonical_handle = HANDLE_ALIAS_MAP.get(raw_handle)
                        if canonical_handle and canonical_handle in users and canonical_handle != 'leila':
                            role = 'VIEWER' if 'VIEWER' in role_str else 'EDITOR'
                            TripMember.objects.get_or_create(
                                trip=trip,
                                user=users[canonical_handle],
                                defaults={'role': role}
                            )

                # Clear existing items for this trip before repopulating
                trip.moves.all().delete()
                trip.stays.all().delete()
                trip.tastes.all().delete()
                trip.plays.all().delete()

                # ----------------------------------------------------
                # 1. MOVES
                # ----------------------------------------------------
                for m_item in doc['move']:
                    m_title = m_item.get('name', 'Move Item')
                    m_status = normalize_status(m_item.get('Status', 'CONFIRMED'), default='CONFIRMED')

                    # Mode mapping
                    raw_mode = clean_val(m_item.get('Mode', ''))
                    if raw_mode in dict(Move.MODE_CHOICES):
                        mode = raw_mode
                    elif 'car' in raw_mode.lower() or 'rental' in raw_mode.lower():
                        mode = 'Car'
                    elif 'train' in raw_mode.lower() or 'rail' in raw_mode.lower():
                        mode = 'Trains'
                    elif 'ferry' in raw_mode.lower() or 'boat' in raw_mode.lower():
                        mode = 'Ferry'
                    elif 'bus' in raw_mode.lower():
                        mode = 'Bus'
                    else:
                        text_corpus = f"{m_title} {m_item.get('Notes', '')}".lower()
                        if any(k in text_corpus for k in ['car', 'rental', 'drive', 'hertz']):
                            mode = 'Car'
                        elif any(k in text_corpus for k in ['train', 'rail', 'trenitalia']):
                            mode = 'Trains'
                        elif any(k in text_corpus for k in ['ferry', 'boat']):
                            mode = 'Ferry'
                        else:
                            mode = 'Planes'

                    # Trip Stage & Direction
                    stage_raw = clean_val(m_item.get('Trip Stage', 'START_END')).upper()
                    trip_stage = 'MID_TRIP' if 'MID' in stage_raw else 'START_END'

                    dir_raw = clean_val(m_item.get('Direction', 'ARRIVING')).upper()
                    direction = 'LEAVING' if ('LEAVING' in dir_raw or 'DEPARTING' in dir_raw) else 'ARRIVING'

                    # Departure & Arrival datetimes
                    m_dept_str = m_item.get('Departure') or m_item.get('Date', '')
                    d_dept = parse_date(m_dept_str)
                    t_dept = parse_time(m_dept_str)

                    dept_dt = None
                    has_dept = False
                    if d_dept and t_dept:
                        dept_dt = timezone.make_aware(datetime.combine(d_dept, t_dept))
                        has_dept = True
                    elif d_dept:
                        dept_dt = timezone.make_aware(datetime.combine(d_dept, time(0, 0)))
                        has_dept = False

                    m_arr_str = m_item.get('Arrival', '')
                    d_arr = parse_date(m_arr_str)
                    t_arr = parse_time(m_arr_str)

                    arr_dt = None
                    has_arr = False
                    if d_arr and t_arr:
                        arr_dt = timezone.make_aware(datetime.combine(d_arr, t_arr))
                        has_arr = True
                    elif d_arr:
                        arr_dt = timezone.make_aware(datetime.combine(d_arr, time(0, 0)))
                        has_arr = False

                    company = m_item.get('Company') or m_item.get('Flight', '')
                    if not company:
                        for comp in ['Delta', 'Alaska Airlines', 'KM Malta', 'United', 'Hertz', 'Trenitalia']:
                            if comp.lower() in f"{m_title} {m_item.get('Notes', '')}".lower():
                                company = comp
                                break

                    move = Move(
                        trip=trip,
                        title=m_title,
                        status=m_status,
                        mode=mode,
                        company=company,
                        trip_stage=trip_stage,
                        direction=direction,
                        origin_address=m_item.get('Origin', ''),
                        destination_address=m_item.get('Destination', ''),
                        departure_time=dept_dt,
                        has_departure_time=has_dept,
                        arrival_time=arr_dt,
                        has_arrival_time=has_arr,
                        flexibility_notes=m_item.get('Notes', ''),
                        description=m_item.get('Description', ''),
                        created_by=leila_user
                    )
                    code = m_item.get('Confirmation/Reference') or m_item.get('Confirmation Code')
                    if code:
                        move.confirmation_code = code
                    move.save()

                # ----------------------------------------------------
                # 2. STAYS
                # ----------------------------------------------------
                for s_item in doc['stay']:
                    s_title = s_item.get('name', 'Stay Item')
                    s_status = normalize_status(s_item.get('Status', 'CONFIRMED'), default='CONFIRMED')

                    # Place Type
                    raw_place = clean_val(s_item.get('Place Type', 'Hotel'))
                    if raw_place in dict(Stay.PLACE_TYPE_CHOICES):
                        place_type = raw_place
                    elif any(k in f"{s_title} {raw_place}".lower() for k in ['home', 'house', 'retreat', 'cabin', 'oasis', 'airbnb']):
                        place_type = 'Home'
                    elif 'apartment' in f"{s_title} {raw_place}".lower():
                        place_type = 'Apartment'
                    else:
                        place_type = 'Hotel'

                    # Check-in and check-out parsing
                    dates_val = s_item.get('Dates', '')
                    parts = re.split(r'[-–—]', dates_val) if dates_val else []
                    s_str = parts[0].strip() if len(parts) >= 1 else s_item.get('Start Date', '')
                    e_str = parts[1].strip() if len(parts) >= 2 else s_item.get('End Date', '')

                    s_d = parse_date(s_str)
                    e_d = parse_date(e_str)
                    s_t = parse_time(s_str)
                    e_t = parse_time(e_str)

                    has_ci = s_t is not None
                    has_co = e_t is not None

                    check_in = timezone.make_aware(datetime.combine(s_d, s_t or time(15, 0))) if s_d else None
                    check_out = timezone.make_aware(datetime.combine(e_d, e_t or time(11, 0))) if e_d else None

                    stay = Stay(
                        trip=trip,
                        title=s_title,
                        status=s_status,
                        place_type=place_type,
                        address=s_item.get('Location', ''),
                        check_in=check_in,
                        check_out=check_out,
                        has_check_in_time=has_ci,
                        has_check_out_time=has_co,
                        notes=s_item.get('Notes', ''),
                        description=s_item.get('Description', ''),
                        created_by=leila_user
                    )
                    code = s_item.get('Confirmation/Reference') or s_item.get('Confirmation Code')
                    if code:
                        stay.confirmation_code = code

                    # Price extraction
                    p_val = s_item.get('Price')
                    if p_val:
                        m_price = re.search(r'\$(\d+(?:\.\d{2})?)', p_val)
                        if m_price:
                            stay.total_price = Decimal(m_price.group(1))
                    elif s_item.get('Notes'):
                        m_price_note = re.search(r'Total:\s*\$(\d+(?:\.\d{2})?)', s_item['Notes'])
                        if m_price_note:
                            stay.total_price = Decimal(m_price_note.group(1))

                    stay.save()

                # ----------------------------------------------------
                # 3. TASTES
                # ----------------------------------------------------
                for t_item in doc['taste']:
                    t_title = t_item.get('name', 'Taste Item')
                    t_status = normalize_status(t_item.get('Status', 'IDEA'), default='IDEA')

                    raw_taste_type = clean_val(t_item.get('Taste Type', 'Food'))
                    if raw_taste_type in dict(Taste.TASTE_TYPE_CHOICES):
                        taste_type = raw_taste_type
                    elif any(k in f"{t_title} {t_item.get('Description', '')}".lower() for k in ['bar', 'beer', 'brewery', 'cocktail', 'wine', 'cafe', 'coffee', 'drink']):
                        taste_type = 'Drink'
                    else:
                        taste_type = 'Food'

                    price_r = t_item.get('Price', '$$')
                    if price_r not in ['$', '$$', '$$$', '$$$$']:
                        price_r = '$$'

                    taste = Taste(
                        trip=trip,
                        title=t_title,
                        status=t_status,
                        taste_type=taste_type,
                        address=t_item.get('Location', ''),
                        price_range=price_r,
                        description=t_item.get('Description', ''),
                        notes=t_item.get('Notes', ''),
                        created_by=leila_user
                    )
                    code = t_item.get('Confirmation/Reference') or t_item.get('Confirmation Code')
                    if code:
                        taste.confirmation_code = code
                    taste.save()

                # ----------------------------------------------------
                # 4. PLAYS
                # ----------------------------------------------------
                for p_item in doc['play']:
                    p_title = p_item.get('name', 'Play Item')
                    p_status = normalize_status(p_item.get('Status', 'IDEA'), default='IDEA')

                    raw_play_type = clean_val(p_item.get('Play Type', 'Sightseeing'))
                    if raw_play_type in dict(Play.PLAY_TYPE_CHOICES):
                        play_type = raw_play_type
                    else:
                        corpus = f"{p_title} {p_item.get('Description', '')} {p_item.get('Notes', '')}".lower()
                        if any(k in corpus for k in ['tour', 'walk', 'excursion']):
                            play_type = 'Tours'
                        elif any(k in corpus for k in ['hike', 'canyon', 'beach', 'sunset', 'water', 'boat', 'blue lagoon', 'outdoors']):
                            play_type = 'Outdoors'
                        elif any(k in corpus for k in ['concert', 'show', 'festival', 'party', 'nightlife', 'event']):
                            play_type = 'Events'
                        else:
                            play_type = 'Sightseeing'

                    p_date = parse_date(p_item.get('Date') or p_item.get('Schedule', ''))
                    time_range = p_item.get('Time') or p_item.get('Schedule', '')
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
                        created_by=leila_user
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
                f"\nSuccessfully imported all {len(imported_trips)} canonical seed trips associated with @leila!"
            ))
