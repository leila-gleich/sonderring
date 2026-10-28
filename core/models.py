import uuid
import calendar
import hashlib
from django.db import models
from django.utils import timezone
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
        ('IDEA', 'Idea'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETE', 'Complete'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='IDEA',
        help_text="Lifecycle state of the trip: Idea (Tentative), Confirmed, or Complete"
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trips'
        verbose_name = 'Trip'
        verbose_name_plural = 'Trips'
        indexes = [
            models.Index(fields=['created_by', 'year'], name='idx_trip_creator_year'),
            models.Index(fields=['status'], name='idx_trip_status'),
        ]

    def __str__(self):
        return self.title

    @property
    def formatted_dates(self):
        if self.time_granularity == 'EXACT_RANGE' and self.start_date and self.end_date:
            if self.start_date.year == self.end_date.year:
                if self.start_date.month == self.end_date.month:
                    return f"{self.start_date.strftime('%b %d')} – {self.end_date.strftime('%d, %Y')}"
                return f"{self.start_date.strftime('%b %d')} – {self.end_date.strftime('%b %d, %Y')}"
            return f"{self.start_date.strftime('%b %d, %Y')} – {self.end_date.strftime('%b %d, %Y')}"
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
        return self.stays.count() + self.navs.count() + self.dos.count()

    @property
    def confirmed_items_count(self):
        return (
            self.stays.filter(status='CONFIRMED').count() +
            self.navs.filter(status='CONFIRMED').count() +
            self.dos.filter(status='CONFIRMED').count()
        )

    @property
    def idea_items_count(self):
        return (
            self.stays.filter(status='IDEA').count() +
            self.navs.filter(status='IDEA').count() +
            self.dos.filter(status='IDEA').count()
        )


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
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed')]
    PLACE_TYPE_CHOICES = [
        ('Hotel Room', 'Hotel Room'),
        ('Entire Place', 'Entire Place'),
        ('Shared Room/Guest House', 'Shared Room/Guest House'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stays')
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    place_type = models.CharField(max_length=50, choices=PLACE_TYPE_CHOICES, blank=True, null=True, default='Hotel Room')
    num_beds = models.IntegerField(blank=True, null=True)
    num_rooms = models.IntegerField(blank=True, null=True)
    num_guests = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
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


class Nav(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed')]
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


class Do(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed')]

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


class Rec(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed')]
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
    nav = models.ForeignKey(Nav, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    do = models.ForeignKey(Do, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    rec = models.ForeignKey(Rec, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
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

