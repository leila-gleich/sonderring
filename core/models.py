import uuid
from django.db import models
from .encryption import ConfirmationEncryptor

class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    handle = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    profile_image_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.full_name} (@{self.handle})"


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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255)
    time_granularity = models.CharField(max_length=20, choices=GRANULARITY_CHOICES)
    season = models.CharField(max_length=10, choices=SEASON_CHOICES, blank=True, null=True)
    year = models.IntegerField()
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    start_month = models.IntegerField(blank=True, null=True)
    end_month = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='created_trips')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trips'
        verbose_name = 'Trip'
        verbose_name_plural = 'Trips'
        indexes = [
            models.Index(fields=['created_by', 'year'], name='idx_trip_creator_year'),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(time_granularity='SEASON_YEAR', season__isnull=False) |
                    models.Q(time_granularity='EXACT_RANGE', start_date__isnull=False, end_date__isnull=False, start_date__lte=models.F('end_date')) |
                    (models.Q(time_granularity='MONTH', start_month__isnull=False) & (models.Q(end_month__isnull=True) | models.Q(start_month__lte=models.F('end_month')))) |
                    models.Q(time_granularity='YEAR')
                ),
                name='chk_trip_time_granularity'
            ),
        ]

    def __str__(self):
        return self.title


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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stays')
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    booking_link = models.URLField(blank=True, null=True)
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_stays')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stays'
        verbose_name = 'Stay'
        verbose_name_plural = 'Stays'
        indexes = [
            models.Index(fields=['trip', 'status', 'check_in'], name='idx_stay_trip_status_checkin'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(check_out__isnull=True) | models.Q(check_in__isnull=True) | models.Q(check_out__gte=models.F('check_in')),
                name='chk_stay_dates'
            ),
        ]

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value)

    def __str__(self):
        return f"{self.title} ({self.status})"


class Nav(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='navs')
    title = models.CharField(max_length=150)
    mode = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDEA')
    description = models.TextField(blank=True, null=True)
    origin_address = models.TextField(blank=True, null=True)
    destination_address = models.TextField(blank=True, null=True)
    departure_time = models.DateTimeField(blank=True, null=True)
    arrival_time = models.DateTimeField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    booking_link = models.URLField(blank=True, null=True)
    _encrypted_confirmation_code = models.TextField(db_column='encrypted_confirmation_code', blank=True, null=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_navs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'navs'
        verbose_name = 'Nav'
        verbose_name_plural = 'Navs'
        indexes = [
            models.Index(fields=['trip', 'status', 'departure_time'], name='idx_nav_trip_status_dept'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(arrival_time__isnull=True) | models.Q(departure_time__isnull=True) | models.Q(arrival_time__gte=models.F('departure_time')),
                name='chk_nav_times'
            ),
        ]

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value)

    def __str__(self):
        return f"{self.title} - {self.mode} ({self.status})"


class Do(models.Model):
    STATUS_CHOICES = [('IDEA', 'Idea'), ('CONFIRMED', 'Confirmed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='dos')
    title = models.CharField(max_length=150)
    activity_type = models.CharField(max_length=50, blank=True, null=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dos'
        verbose_name = 'Do'
        verbose_name_plural = 'Dos'
        indexes = [
            models.Index(fields=['trip', 'status', 'start_time'], name='idx_do_trip_status_start'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__isnull=True) | models.Q(start_time__isnull=True) | models.Q(end_time__gte=models.F('start_time')),
                name='chk_do_times'
            ),
        ]

    @property
    def confirmation_code(self):
        return ConfirmationEncryptor.decrypt(self._encrypted_confirmation_code)

    @confirmation_code.setter
    def confirmation_code(self, value):
        self._encrypted_confirmation_code = ConfirmationEncryptor.encrypt(value)

    def __str__(self):
        return f"{self.title} ({self.status})"


class Attachment(models.Model):
    """Secure Vault document attachment."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='attachments')
    stay = models.ForeignKey(Stay, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    nav = models.ForeignKey(Nav, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    do = models.ForeignKey(Do, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    file_name = models.CharField(max_length=255)
    storage_path = models.TextField()
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_attachments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attachments'
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments (Vault)'
        indexes = [
            models.Index(fields=['trip', 'created_at'], name='idx_att_trip_created'),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(stay__isnull=True) & models.Q(nav__isnull=True) & models.Q(do__isnull=True)) |
                    (models.Q(stay__isnull=False) & models.Q(nav__isnull=True) & models.Q(do__isnull=True)) |
                    (models.Q(stay__isnull=True) & models.Q(nav__isnull=False) & models.Q(do__isnull=True)) |
                    (models.Q(stay__isnull=True) & models.Q(nav__isnull=True) & models.Q(do__isnull=False))
                ),
                name='chk_attachment_target'
            ),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.trip.title})"
