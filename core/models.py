import uuid
import calendar
import hashlib
import secrets
from django.db import models
from django.db.models import Case, When, Value, IntegerField, F
from django.db.models.functions import ExtractYear, ExtractMonth, ExtractDay
from django.utils import timezone
from django.utils.dateparse import parse_date
from .encryption import ConfirmationEncryptor, EncryptedCharField, EncryptedTextField

class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    handle = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=100)
    password = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text="Hashed password (standard Django PBKDF2/Argon2)."
    )
    phone_number = EncryptedCharField(
        max_length=255,
        blank=True,
        null=True,
        aad_context='user:phone_number',
        help_text="AES-256-GCM encrypted phone number."
    )
    profile_image_url = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.full_name} (@{self.handle})"

    def set_password(self, raw_password):
        """Hashes and sets the user's password using Django's default hasher."""
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifies a raw password against the stored hash."""
        from django.contrib.auth.hashers import check_password
        if not self.password:
            return False
        return check_password(raw_password, self.password)

    def has_usable_password(self):
        """Returns True if the user has a valid password hash set."""
        if not self.password:
            return False
        from django.contrib.auth.hashers import is_password_usable
        return is_password_usable(self.password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def has_oauth_provider(self, provider='google'):
        """Checks if the user has linked a specific OAuth provider."""
        return self.oauth_identities.filter(provider=provider).exists()

    def get_oauth_identity(self, provider='google'):
        """Returns the OAuth identity record for a provider, or None."""
        return self.oauth_identities.filter(provider=provider).first()


class OAuthIdentity(models.Model):
    """
    Decoupled OAuth / Social identity record.
    Maps an external provider account (e.g. Google, Apple) to an internal UserProfile.
    If OAuth is disabled or uninstalled, UserProfile and all trips remain 100% intact.
    """
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('apple', 'Apple'),
        ('github', 'GitHub'),
        ('microsoft', 'Microsoft'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='oauth_identities'
    )
    provider = models.CharField(
        max_length=30,
        choices=PROVIDER_CHOICES,
        default='google',
        help_text="OAuth provider identifier (e.g. google, apple)"
    )
    uid = models.CharField(
        max_length=255,
        help_text="Unique external subject/user ID provided by the OAuth service"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Verified email returned by the provider during OAuth flow"
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON payload containing provider claims (avatar, name, locale)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oauth_identities'
        verbose_name = 'OAuth Identity'
        verbose_name_plural = 'OAuth Identities'
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'uid'],
                name='uq_oauth_provider_uid'
            ),
            models.UniqueConstraint(
                fields=['user', 'provider'],
                name='uq_oauth_user_provider'
            ),
        ]
        indexes = [
            models.Index(fields=['provider', 'uid'], name='idx_oauth_provider_uid'),
            models.Index(fields=['user', 'provider'], name='idx_oauth_user_provider'),
        ]

    def __str__(self):
        return f"{self.user.handle} — {self.get_provider_display()} ({self.uid})"


class Trip(models.Model):
    GRANULARITY_CHOICES = [
        ('SEASON_YEAR', 'Season & Year'),
        ('EXACT_RANGE', 'Exact Date Range'),
        ('MONTH', 'Month Span'),
        ('YEAR', 'Year'),
    ]
    SEASON_CHOICES = [
        ('SPRING', 'Spring'),
        ('SUMMER', 'Summer'),
        ('FALL', 'Fall'),
        ('WINTER', 'Winter'),
    ]
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('CURRENT', 'Current'),
        ('PAST', 'Past'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UPCOMING',
        help_text="Lifecycle state of the TripSpace: Upcoming, Current, or Past"
    )
    time_granularity = models.CharField(max_length=20, choices=GRANULARITY_CHOICES, default='YEAR')
    season = models.CharField(max_length=10, choices=SEASON_CHOICES, blank=True, null=True)
    year = models.IntegerField(default=2026)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    start_month = models.IntegerField(blank=True, null=True)
    end_month = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='created_trips')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_trips')
    rec_token = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        help_text="Public recommendation invite token for non-trippers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trips'
        verbose_name = 'Trip'
        verbose_name_plural = 'Trips'
        indexes = [
            models.Index(fields=['created_by', 'year'], name='idx_trip_creator_year'),
            models.Index(fields=['status'], name='idx_trip_status'),
            models.Index(fields=['rec_token'], name='idx_trip_rec_token'),
        ]

    def save(self, *args, **kwargs):
        if not self.rec_token:
            self.rec_token = secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def formatted_dates(self):
        s_date = parse_date(self.start_date) if isinstance(self.start_date, str) else self.start_date
        e_date = parse_date(self.end_date) if isinstance(self.end_date, str) else self.end_date
        if self.time_granularity == 'EXACT_RANGE' and s_date and e_date:
            if s_date.year == e_date.year:
                if s_date.month == e_date.month:
                    return f"{s_date.strftime('%b %d')} – {e_date.strftime('%d, %Y')}"
                return f"{s_date.strftime('%b %d')} – {e_date.strftime('%b %d, %Y')}"
            return f"{s_date.strftime('%b %d, %Y')} – {e_date.strftime('%b %d, %Y')}"
        elif self.time_granularity == 'SEASON_YEAR' and self.season:
            return f"{self.get_season_display()} {self.year}"
        elif self.time_granularity == 'MONTH' and self.start_month:
            start_m = calendar.month_name[self.start_month]
            if self.end_month and self.end_month != self.start_month:
                end_m = calendar.month_name[self.end_month]
                return f"{start_m} – {end_m} {self.year}"
            return f"{start_m} {self.year}"
        elif self.year:
            return f"{self.year} Season"
        return "Dates TBD"

    @property
    def total_items_count(self):
        return self.moves.count() + self.stays.count() + self.tastes.count() + self.plays.count()

    @property
    def confirmed_items_count(self):
        return (
            self.moves.filter(status='CONFIRMED').count() +
            self.stays.filter(status='CONFIRMED').count() +
            self.tastes.filter(status='CONFIRMED').count() +
            self.plays.filter(status='CONFIRMED').count()
        )

    @property
    def idea_items_count(self):
        return (
            self.moves.filter(status='IDEA').count() +
            self.stays.filter(status='IDEA').count() +
            self.tastes.filter(status='IDEA').count() +
            self.plays.filter(status='IDEA').count()
        )

    @property
    def complete_items_count(self):
        return (
            self.moves.filter(status='COMPLETE').count() +
            self.stays.filter(status='COMPLETE').count() +
            self.tastes.filter(status='COMPLETE').count() +
            self.plays.filter(status='COMPLETE').count()
        )

    # Backward compatibility properties
    @property
    def navs(self):
        return self.moves

    @property
    def dos(self):
        return self.plays

    @property
    def recs(self):
        return self.tastes

    @classmethod
    def get_current_and_upcoming(cls, queryset=None):
        """Returns active/upcoming trips sorted with CURRENT first (farthest left), then chronological."""
        if queryset is None:
            queryset = cls.objects.all()
        return order_current_and_upcoming_trips(queryset)


def order_current_and_upcoming_trips(queryset_or_list):
    """
    Filters and orders trips for the 'Current & Upcoming Trips' section:
    1. CURRENT trip(s) appear first (farthest left in dashboard grid).
    2. Within CURRENT and UPCOMING statuses, trips are ordered chronologically
       by year, month, and day (earliest to latest).
    Supports all 4 hybrid time granularities (EXACT_RANGE, MONTH, SEASON_YEAR, YEAR).
    """
    if hasattr(queryset_or_list, 'filter') and hasattr(queryset_or_list, 'annotate'):
        return queryset_or_list.filter(status__in=['CURRENT', 'UPCOMING']).distinct().annotate(
            status_priority=Case(
                When(status='CURRENT', then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            ),
            sort_year=Case(
                When(time_granularity='EXACT_RANGE', start_date__isnull=False, then=ExtractYear('start_date')),
                When(start_date__isnull=False, then=ExtractYear('start_date')),
                default=F('year'),
                output_field=IntegerField()
            ),
            sort_month=Case(
                When(time_granularity='EXACT_RANGE', start_date__isnull=False, then=ExtractMonth('start_date')),
                When(time_granularity='MONTH', start_month__isnull=False, then=F('start_month')),
                When(time_granularity='SEASON_YEAR', season='SPRING', then=Value(3)),
                When(time_granularity='SEASON_YEAR', season='SUMMER', then=Value(6)),
                When(time_granularity='SEASON_YEAR', season='FALL', then=Value(9)),
                When(time_granularity='SEASON_YEAR', season='WINTER', then=Value(12)),
                When(start_date__isnull=False, then=ExtractMonth('start_date')),
                When(start_month__isnull=False, then=F('start_month')),
                default=Value(1),
                output_field=IntegerField()
            ),
            sort_day=Case(
                When(time_granularity='EXACT_RANGE', start_date__isnull=False, then=ExtractDay('start_date')),
                When(start_date__isnull=False, then=ExtractDay('start_date')),
                default=Value(1),
                output_field=IntegerField()
            )
        ).order_by('status_priority', 'sort_year', 'sort_month', 'sort_day', 'title', 'id')

    # Python list/iterable fallback
    season_months = {'SPRING': 3, 'SUMMER': 6, 'FALL': 9, 'WINTER': 12}

    def trip_sort_key(t):
        prio = 0 if getattr(t, 'status', None) == 'CURRENT' else 1
        s_date = getattr(t, 'start_date', None)
        granularity = getattr(t, 'time_granularity', 'YEAR')
        yr = s_date.year if (s_date and hasattr(s_date, 'year')) else (getattr(t, 'year', None) or 0)
        
        if granularity == 'EXACT_RANGE' and s_date and hasattr(s_date, 'month'):
            mo = s_date.month
        elif granularity == 'MONTH' and getattr(t, 'start_month', None):
            mo = t.start_month
        elif granularity == 'SEASON_YEAR' and getattr(t, 'season', None):
            mo = season_months.get(t.season, 1)
        elif s_date and hasattr(s_date, 'month'):
            mo = s_date.month
        elif getattr(t, 'start_month', None):
            mo = t.start_month
        else:
            mo = 1

        day = s_date.day if (s_date and hasattr(s_date, 'day')) else 1
        return (prio, yr, mo, day, getattr(t, 'title', '') or '', str(getattr(t, 'id', '')))

    filtered = [t for t in queryset_or_list if getattr(t, 'status', None) in ('CURRENT', 'UPCOMING')]
    return sorted(filtered, key=trip_sort_key)


class TripMember(models.Model):
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('EDITOR', 'Editor'),
        ('VIEWER', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='trip_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EDITOR')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trip_members'
        unique_together = ('trip', 'user')
        verbose_name = 'Trip Member'
        verbose_name_plural = 'Trip Members'
        indexes = [
            models.Index(fields=['user', 'role'], name='idx_trip_member_user_role'),
        ]

    def __str__(self):
        return f"{self.user.handle} in {self.trip.title} ({self.role})"


class Stay(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed'), ('COMPLETE', 'Complete')]
    PLACE_TYPE_CHOICES = [
        ('Hotel', 'Hotel'),
        ('Home', 'Home'),
        ('Apartment', 'Apartment'),
        ('Room', 'Room'),
        ('Bed', 'Bed'),
        # Legacy mappings for backward compatibility
        ('Hotel Room', 'Hotel'),
        ('Entire Place', 'Home'),
        ('Shared Room/Guest House', 'Room'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stays')
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    place_type = models.CharField(max_length=50, choices=PLACE_TYPE_CHOICES, blank=True, null=True, default='Hotel')
    stay_length = models.IntegerField(blank=True, null=True, help_text="Stay duration value")
    stay_length_unit = models.CharField(
        max_length=20,
        choices=[('Days', 'Day(s)'), ('Weeks', 'Week(s)'), ('Months', 'Month(s)')],
        default='Days',
        blank=True,
        null=True
    )
    num_beds = models.IntegerField(blank=True, null=True)
    num_rooms = models.IntegerField(blank=True, null=True)
    num_guests = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    has_check_in_time = models.BooleanField(default=False)
    has_check_out_time = models.BooleanField(default=False)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    booking_link = models.URLField(blank=True, null=True)
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    notes = EncryptedTextField(
        blank=True,
        null=True,
        aad_context='stay:notes',
        help_text="AES-256-GCM encrypted check-in instructions, keypad codes, and door notes."
    )
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_stays')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_stays')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stays'
        verbose_name = 'Stay'
        verbose_name_plural = 'Stays'
        indexes = [
            models.Index(fields=['trip', 'status', 'check_in'], name='idx_stay_trip_status_checkin'),
        ]

    @property
    def location(self):
        return self.address

    @location.setter
    def location(self, val):
        self.address = val

    @property
    def link(self):
        return self.booking_link

    @link.setter
    def link(self, val):
        self.booking_link = val

    @property
    def price(self):
        return self.total_price

    @price.setter
    def price(self, val):
        self.total_price = val

    @property
    def _confirmation_aad(self) -> str:
        return f"stay:{self.trip_id}" if self.trip_id else "stay"

    @property
    def has_confirmation_code(self):
        return bool(self._encrypted_confirmation_code)

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code, aad=self._confirmation_aad)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value, aad=self._confirmation_aad)

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_check_in_time_set(self):
        return self.has_check_in_time or (bool(self.check_in) and (self.check_in.hour != 0 or self.check_in.minute != 0))

    @property
    def is_check_out_time_set(self):
        return self.has_check_out_time or (bool(self.check_out) and (self.check_out.hour != 0 or self.check_out.minute != 0))

    @property
    def check_in_time_str(self):
        if self.check_in and self.is_check_in_time_set:
            return self.check_in.strftime('%H:%M')
        return ''

    @property
    def check_out_time_str(self):
        if self.check_out and self.is_check_out_time_set:
            return self.check_out.strftime('%H:%M')
        return ''


class Move(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed'), ('COMPLETE', 'Complete')]
    STAGE_CHOICES = [
        ('START_END', 'Trip Start/End'),
        ('MID_TRIP', 'Mid-Trip'),
    ]
    DIRECTION_CHOICES = [
        ('ARRIVING', 'Arriving to Trip'),
        ('LEAVING', 'Leaving Trip'),
    ]
    CONFIDENCE_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('TENTATIVE', 'Tentative'),
    ]
    MODE_CHOICES = [
        ('Planes', 'Planes'),
        ('Trains', 'Trains'),
        ('Car', 'Car'),
        # Legacy mappings for backward compatibility
        ('Flight', 'Planes'),
        ('Train', 'Trains'),
        ('Ferry', 'Ferry'),
        ('Bus', 'Bus'),
        ('Rideshare', 'Car'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='moves')
    title = models.CharField(max_length=150)
    mode = models.CharField(max_length=50, choices=MODE_CHOICES, default='Planes') # Planes, Trains, Car
    company = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Company or operator (airline, train line, car rental)"
    )
    trip_stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='START_END')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='ARRIVING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    passenger_name = EncryptedCharField(
        max_length=255,
        blank=True,
        null=True,
        aad_context='move:passenger_name',
        help_text="AES-256-GCM encrypted passenger name."
    )
    description = models.TextField(blank=True, null=True)
    origin_address = models.TextField(blank=True, null=True)
    destination_address = models.TextField(blank=True, null=True)
    departure_time = models.DateTimeField(blank=True, null=True)
    arrival_time = models.DateTimeField(blank=True, null=True)
    has_departure_time = models.BooleanField(default=False)
    has_arrival_time = models.BooleanField(default=False)
    date_confidence = models.CharField(max_length=20, choices=CONFIDENCE_CHOICES, default='CONFIRMED')
    time_confidence = models.CharField(max_length=20, choices=CONFIDENCE_CHOICES, default='CONFIRMED')
    flexibility_notes = EncryptedTextField(
        blank=True,
        null=True,
        aad_context='move:flexibility_notes',
        help_text="AES-256-GCM encrypted transit flexibility & ticket notes."
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    booking_link = models.URLField(blank=True, null=True)
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_moves')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_moves')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'moves'
        verbose_name = 'Move'
        verbose_name_plural = 'Moves'
        indexes = [
            models.Index(fields=['trip', 'status', 'departure_time'], name='idx_move_trip_status_dept'),
        ]

    @property
    def link(self):
        return self.booking_link

    @link.setter
    def link(self, val):
        self.booking_link = val

    @property
    def notes(self):
        return self.flexibility_notes

    @notes.setter
    def notes(self, val):
        self.flexibility_notes = val

    @property
    def _confirmation_aad(self) -> str:
        return f"move:{self.trip_id}" if self.trip_id else "move"

    @property
    def has_confirmation_code(self):
        return bool(self._encrypted_confirmation_code)

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code, aad=self._confirmation_aad)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value, aad=self._confirmation_aad)

    def __str__(self):
        return f"{self.title} - {self.mode} ({self.status})"

    @property
    def date(self):
        return self.departure_time.date() if self.departure_time else None

    @property
    def is_departure_time_set(self):
        return self.has_departure_time or (bool(self.departure_time) and (self.departure_time.hour != 0 or self.departure_time.minute != 0))

    @property
    def is_arrival_time_set(self):
        return self.has_arrival_time or (bool(self.arrival_time) and (self.arrival_time.hour != 0 or self.arrival_time.minute != 0))

    @property
    def departure_time_str(self):
        if self.departure_time and self.is_departure_time_set:
            return self.departure_time.strftime('%H:%M')
        return ''

    @property
    def arrival_time_str(self):
        if self.arrival_time and self.is_arrival_time_set:
            return self.arrival_time.strftime('%H:%M')
        return ''


class Taste(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed'), ('COMPLETE', 'Complete')]
    PRICE_RANGE_CHOICES = [
        ('$', '$'),
        ('$$', '$$'),
        ('$$$', '$$$'),
        ('$$$$', '$$$$'),
    ]
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Drink', 'Drink'),
    ]
    LEGACY_TASTE_TYPE_MAP = {
        'Restaurant': 'Food',
        'Food Market': 'Food',
        'Culinary Tour': 'Food',
        'Cooking Class': 'Food',
        'Dessert': 'Food',
        'Bar & Drinks': 'Drink',
        'Winery & Brewery': 'Drink',
        'Cafe & Bakery': 'Drink',
        'Coffee': 'Drink',
        'Cafe': 'Drink',
    }
    TASTE_TYPE_CHOICES = CATEGORY_CHOICES + [
        ('Cafe', 'Drink'),
        ('Restaurant', 'Food'),
        ('Bar & Drinks', 'Drink'),
        ('Cafe & Bakery', 'Drink'),
        ('Winery & Brewery', 'Drink'),
        ('Food Market', 'Food'),
        ('Culinary Tour', 'Food'),
        ('Dessert', 'Food'),
        ('Coffee', 'Drink'),
        ('Cooking Class', 'Food'),
    ]
    CUISINE_CHOICES = [
        ('American', 'American'),
        ('African', 'African'),
        ('Asian', 'Asian'),
        ('Contemporary', 'Contemporary'),
        ('European', 'European'),
        ('Fusion', 'Fusion'),
        ('Indian', 'Indian'),
        ('Mediterranean', 'Mediterranean'),
        ('Mexican', 'Mexican'),
        ('South American', 'South American'),
    ]
    DRINK_CATEGORY_CHOICES = [
        ('Beer', 'Beer'),
        ('Cocktails', 'Cocktails'),
        ('Wine', 'Wine'),
        ('Tea & Coffee', 'Tea & Coffee'),
        ('Juice and Smoothies', 'Juice and Smoothies'),
        ('Other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='tastes')
    title = models.CharField(max_length=150)
    taste_type = models.CharField(max_length=50, choices=TASTE_TYPE_CHOICES, default='Food')
    cuisine = models.CharField(
        max_length=50,
        choices=CUISINE_CHOICES,
        blank=True,
        null=True,
        help_text="Cuisine type if Food"
    )
    drink_category = models.CharField(
        max_length=50,
        choices=DRINK_CATEGORY_CHOICES,
        blank=True,
        null=True,
        help_text="Beverage category if Drink"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    has_start_time = models.BooleanField(default=False)
    has_end_time = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_range = models.CharField(
        max_length=10,
        choices=PRICE_RANGE_CHOICES,
        blank=True,
        null=True,
        help_text="Price range tier ($ to $$$$)"
    )
    currency = models.CharField(max_length=3, default='USD')
    link = models.URLField(blank=True, null=True)
    menu_link = models.URLField(blank=True, null=True, help_text="Link to menu")
    general_link = models.URLField(blank=True, null=True, help_text="General website or resource link")
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    notes = EncryptedTextField(
        blank=True,
        null=True,
        aad_context='taste:notes',
        help_text="AES-256-GCM encrypted reservation notes, table requests, or dietary details."
    )
    guest_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name or nickname of non-tripper contributor"
    )
    recommended_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommended_tastes')
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tastes')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_tastes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tastes'
        verbose_name = 'Taste'
        verbose_name_plural = 'Tastes'
        indexes = [
            models.Index(fields=['trip', 'status', 'start_time'], name='idx_taste_trip_status_start'),
        ]

    @property
    def location(self):
        return self.address

    @location.setter
    def location(self, val):
        self.address = val

    @property
    def booking_reference(self):
        return self.confirmation_code

    @booking_reference.setter
    def booking_reference(self, val):
        self.confirmation_code = val

    @property
    def _confirmation_aad(self) -> str:
        return f"taste:{self.trip_id}" if self.trip_id else "taste"

    @property
    def has_confirmation_code(self):
        return bool(self._encrypted_confirmation_code)

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code, aad=self._confirmation_aad)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value, aad=self._confirmation_aad)

    @property
    def category(self):
        return self.get_taste_type_display() if hasattr(self, 'get_taste_type_display') else self.taste_type

    @property
    def effective_menu_link(self):
        return self.menu_link or self.link

    def __str__(self):
        return f"{self.title} ({self.taste_type} - {self.status})"

    @property
    def date(self):
        return self.start_time.date() if self.start_time else None

    @property
    def is_start_time_set(self):
        return self.has_start_time or (bool(self.start_time) and (self.start_time.hour != 0 or self.start_time.minute != 0))

    @property
    def is_end_time_set(self):
        return self.has_end_time or (bool(self.end_time) and (self.end_time.hour != 0 or self.end_time.minute != 0))

    @property
    def start_time_str(self):
        if self.start_time and self.is_start_time_set:
            return self.start_time.strftime('%H:%M')
        return ''

    @property
    def end_time_str(self):
        if self.end_time and self.is_end_time_set:
            return self.end_time.strftime('%H:%M')
        return ''


class Play(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed'), ('COMPLETE', 'Complete')]
    PLAY_TYPE_CHOICES = [
        ('Outdoors', 'Outdoors'),
        ('Tours', 'Tours'),
        ('Events', 'Events'),
        ('Sightseeing', 'Sightseeing'),
        ('Other', 'Other'),
        # Legacy mappings for backward compatibility
        ('Activity', 'Outdoors'),
        ('Tour', 'Tours'),
        ('Sight', 'Sightseeing'),
        ('Event', 'Events'),
        ('Hike', 'Outdoors'),
        ('Museum', 'Sightseeing'),
        ('Outdoor & Hike', 'Outdoors'),
        ('Tour & Excursion', 'Tours'),
        ('Culture & Museum', 'Sightseeing'),
        ('Water & Boat', 'Outdoors'),
        ('Nightlife & Music', 'Events'),
        ('Event & Show', 'Events'),
        ('Spa & Wellness', 'Other'),
        ('Travel Tip', 'Other'),
    ]
    PRICE_TIER_CHOICES = [
        ('Free', 'Free'),
        ('$', '$'),
        ('$$', '$$'),
        ('$$$', '$$$'),
        ('$$$$', '$$$$'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='plays')
    title = models.CharField(max_length=150)
    play_type = models.CharField(max_length=50, choices=PLAY_TYPE_CHOICES, default='Sightseeing')
    price_tier = models.CharField(
        max_length=10,
        choices=PRICE_TIER_CHOICES,
        blank=True,
        null=True,
        help_text="Price tier for Play item (Free to $$$$)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    has_start_time = models.BooleanField(default=False)
    has_end_time = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    link = models.URLField(blank=True, null=True)
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    notes = EncryptedTextField(
        blank=True,
        null=True,
        aad_context='play:notes',
        help_text="AES-256-GCM encrypted ticket instructions, entry codes, or tour guides."
    )
    guest_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name or nickname of non-tripper contributor"
    )
    recommended_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommended_plays')
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_plays')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_plays')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'plays'
        verbose_name = 'Play'
        verbose_name_plural = 'Plays'
        indexes = [
            models.Index(fields=['trip', 'status', 'start_time'], name='idx_play_trip_status_start'),
        ]

    @property
    def location(self):
        return self.address

    @location.setter
    def location(self, val):
        self.address = val

    @property
    def _confirmation_aad(self) -> str:
        return f"play:{self.trip_id}" if self.trip_id else "play"

    @property
    def has_confirmation_code(self):
        return bool(self._encrypted_confirmation_code)

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code, aad=self._confirmation_aad)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value, aad=self._confirmation_aad)

    def __str__(self):
        return f"{self.title} ({self.play_type} - {self.status})"

    @property
    def date(self):
        return self.start_time.date() if self.start_time else None

    @property
    def is_start_time_set(self):
        return self.has_start_time or (bool(self.start_time) and (self.start_time.hour != 0 or self.start_time.minute != 0))

    @property
    def is_end_time_set(self):
        return self.has_end_time or (bool(self.end_time) and (self.end_time.hour != 0 or self.end_time.minute != 0))

    @property
    def start_time_str(self):
        if self.start_time and self.is_start_time_set:
            return self.start_time.strftime('%H:%M')
        return ''

    @property
    def end_time_str(self):
        if self.end_time and self.is_end_time_set:
            return self.end_time.strftime('%H:%M')
        return ''


class Nav(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed'), ('COMPLETE', 'Complete')]
    STAGE_CHOICES = [
        ('START_END', 'Trip Start/End'),
        ('MID_TRIP', 'Mid-Trip'),
    ]
    DIRECTION_CHOICES = [
        ('ARRIVING', 'Arriving to Trip'),
        ('LEAVING', 'Leaving Trip'),
    ]
    CONFIDENCE_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('TENTATIVE', 'Tentative'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='navs')
    title = models.CharField(max_length=150)
    mode = models.CharField(max_length=50) # Flight, Train, Ferry, Car, Bus, etc.
    trip_stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='START_END')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='ARRIVING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    passenger_name = EncryptedCharField(
        max_length=255,
        blank=True,
        null=True,
        aad_context='nav:passenger_name',
        help_text="AES-256-GCM encrypted passenger name."
    )
    description = models.TextField(blank=True, null=True)
    origin_address = models.TextField(blank=True, null=True)
    destination_address = models.TextField(blank=True, null=True)
    departure_time = models.DateTimeField(blank=True, null=True)
    arrival_time = models.DateTimeField(blank=True, null=True)
    date_confidence = models.CharField(max_length=20, choices=CONFIDENCE_CHOICES, default='CONFIRMED')
    time_confidence = models.CharField(max_length=20, choices=CONFIDENCE_CHOICES, default='CONFIRMED')
    flexibility_notes = EncryptedTextField(
        blank=True,
        null=True,
        aad_context='nav:flexibility_notes',
        help_text="AES-256-GCM encrypted transit flexibility & ticket notes."
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    booking_link = models.URLField(blank=True, null=True)
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_navs')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_navs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'navs'
        verbose_name = 'Nav'
        verbose_name_plural = 'Navs'
        indexes = [
            models.Index(fields=['trip', 'status', 'departure_time'], name='idx_nav_trip_status_dept'),
        ]

    @property
    def _confirmation_aad(self) -> str:
        return f"nav:{self.trip_id}" if self.trip_id else "nav"

    @property
    def has_confirmation_code(self):
        return bool(self._encrypted_confirmation_code)

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code, aad=self._confirmation_aad)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value, aad=self._confirmation_aad)

    def __str__(self):
        return f"{self.title} - {self.mode} ({self.status})"

    @property
    def date(self):
        return self.departure_time.date() if self.departure_time else None


class Do(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed'), ('COMPLETE', 'Complete')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='dos')
    title = models.CharField(max_length=150)
    activity_type = models.CharField(max_length=50, blank=True, null=True) # Sightseeing, Dining, Tour, Concert, etc.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    link = models.URLField(blank=True, null=True)
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_dos')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_dos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dos'
        verbose_name = 'Do'
        verbose_name_plural = 'Dos'
        indexes = [
            models.Index(fields=['trip', 'status', 'start_time'], name='idx_do_trip_status_start'),
        ]

    @property
    def _confirmation_aad(self) -> str:
        return f"do:{self.trip_id}" if self.trip_id else "do"

    @property
    def has_confirmation_code(self):
        return bool(self._encrypted_confirmation_code)

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code, aad=self._confirmation_aad)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value, aad=self._confirmation_aad)

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def date(self):
        return self.start_time.date() if self.start_time else None


class Rec(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed'), ('COMPLETE', 'Complete')]
    CATEGORY_CHOICES = [
        ('Food', 'Food & Dining'),
        ('Spot', 'Sight & Spot'),
        ('Activity', 'Activity & Experience'),
        ('Tip', 'Travel Tip & Advice'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='recs')
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Food')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    guest_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name or nickname of non-tripper contributor"
    )
    recommended_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommended_recs')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_recs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recs'
        verbose_name = 'Rec'
        verbose_name_plural = 'Recs'
        indexes = [
            models.Index(fields=['trip', 'category'], name='idx_rec_trip_category'),
            models.Index(fields=['trip', 'status'], name='idx_rec_trip_status'),
        ]

    def __str__(self):
        return f"{self.title} ({self.category} - {self.status})"


class Attachment(models.Model):
    """Secure Vault document attachment."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='attachments')
    stay = models.ForeignKey(Stay, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    move = models.ForeignKey(Move, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    taste = models.ForeignKey(Taste, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    play = models.ForeignKey(Play, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    nav = models.ForeignKey(Nav, on_delete=models.CASCADE, null=True, blank=True, related_name='legacy_attachments_nav')
    do = models.ForeignKey(Do, on_delete=models.CASCADE, null=True, blank=True, related_name='legacy_attachments_do')
    rec = models.ForeignKey(Rec, on_delete=models.CASCADE, null=True, blank=True, related_name='legacy_attachments_rec')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, blank=True, default='application/pdf')
    storage_path = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='vault/%Y/%m/', blank=True, null=True)
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_attachments')
    updated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_attachments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attachments'
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments (Vault)'
        indexes = [
            models.Index(fields=['trip', 'created_at'], name='idx_att_trip_created'),
        ]

    def generate_signed_token(self) -> str:
        """Generates a cryptographically signed timestamped token scoped to this trip and attachment."""
        from django.core.signing import TimestampSigner
        signer = TimestampSigner(salt='sonderring.vault.download')
        return signer.sign(f"{self.trip_id}:{self.id}")

    @property
    def signed_download_url(self) -> str:
        """Returns a time-limited (15-min default) pre-signed URL for authorized download."""
        from django.urls import reverse
        from urllib.parse import quote
        base_url = reverse('core:download_attachment', args=[self.trip_id, self.id])
        return f"{base_url}?token={quote(self.generate_signed_token())}"

    def __str__(self):
        return f"{self.file_name} ({self.trip.title})"


class SecurityAuditLog(models.Model):
    """
    Tamper-evident security audit log with SHA-256 hash chaining.
    Records all sensitive credential accesses, vault operations, and role modifications.
    """
    ACTION_CHOICES = [
        ('CONFIRMATION_CODE_REVEALED', 'Confirmation Code Revealed'),
        ('VAULT_DOCUMENT_UPLOADED', 'Vault Document Uploaded'),
        ('VAULT_DOCUMENT_ACCESSED', 'Vault Document Accessed'),
        ('VAULT_DOCUMENT_DELETED', 'Vault Document Deleted'),
        ('MEMBER_INVITED', 'Tripper Invited'),
        ('MEMBER_ROLE_CHANGED', 'Tripper Role Changed'),
        ('MEMBER_REMOVED', 'Tripper Removed'),
        ('AUTH_LOGIN_SUCCESS', 'Authentication Login Success'),
        ('AUTH_LOGIN_FAILED', 'Authentication Login Failed'),
        ('PASSWORD_CHANGED', 'Password Changed'),
        ('TRIP_EXPORTED', 'Trip Exported'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='security_audit_logs'
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    previous_hash = models.CharField(max_length=64, blank=True, default='0' * 64)
    record_hash = models.CharField(max_length=64, blank=True, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'security_audit_logs'
        verbose_name = 'Security Audit Log'
        verbose_name_plural = 'Security Audit Logs'
        ordering = ['timestamp', 'id']
        indexes = [
            models.Index(fields=['trip', 'timestamp'], name='idx_audit_trip_ts'),
            models.Index(fields=['user', 'timestamp'], name='idx_audit_user_ts'),
            models.Index(fields=['action', 'timestamp'], name='idx_audit_action_ts'),
        ]

    def compute_hash(self) -> str:
        ts_iso = self.timestamp.isoformat() if self.timestamp else ''
        payload = (
            f"{self.previous_hash}|{self.action}|{self.trip_id or ''}|"
            f"{self.user_id or ''}|{self.resource_type}|{self.resource_id or ''}|{ts_iso}"
        )
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def save(self, *args, **kwargs):
        if not self.timestamp:
            self.timestamp = timezone.now()
        if not self.record_hash:
            last_log = SecurityAuditLog.objects.order_by('-timestamp', '-id').first()
            self.previous_hash = last_log.record_hash if last_log and last_log.record_hash else ('0' * 64)
            self.record_hash = self.compute_hash()
        super().save(*args, **kwargs)

    @classmethod
    def verify_chain(cls) -> tuple[bool, str | None]:
        """Verifies the cryptographic integrity of the entire audit log chain."""
        expected_prev = '0' * 64
        for log in cls.objects.order_by('timestamp', 'id'):
            if log.previous_hash != expected_prev:
                return False, f"Broken hash chain link at audit record {log.id}"
            if log.compute_hash() != log.record_hash:
                return False, f"Tampered record payload detected at audit record {log.id}"
            expected_prev = log.record_hash
        return True, None

    def __str__(self):
        actor = f"@{self.user.handle}" if self.user else "anonymous"
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.action} by {actor} on {self.resource_type}"

