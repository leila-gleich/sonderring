from django.contrib import admin
from .models import UserProfile, Trip, TripMember, Stay, Move, Taste, Play, Attachment, OAuthIdentity, SecurityAuditLog


class OAuthIdentityInline(admin.TabularInline):
    model = OAuthIdentity
    extra = 0
    readonly_fields = ('provider', 'uid', 'email', 'created_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('handle', 'full_name', 'email', 'is_active', 'last_login', 'created_at')
    search_fields = ('handle', 'full_name', 'email')
    list_filter = ('is_active',)
    ordering = ('-created_at',)
    inlines = [OAuthIdentityInline]


@admin.register(OAuthIdentity)
class OAuthIdentityAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'uid', 'email', 'created_at')
    list_filter = ('provider',)
    search_fields = ('user__handle', 'user__email', 'uid', 'email')


class TripMemberInline(admin.TabularInline):
    model = TripMember
    extra = 1


class StayInline(admin.StackedInline):
    model = Stay
    extra = 0


class MoveInline(admin.StackedInline):
    model = Move
    extra = 0


class TasteInline(admin.StackedInline):
    model = Taste
    extra = 0


class PlayInline(admin.StackedInline):
    model = Play
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'status', 'time_granularity', 'season', 'year', 'created_by', 'created_at')
    list_filter = ('status', 'time_granularity', 'season', 'year')
    search_fields = ('title', 'location', 'description')
    inlines = [TripMemberInline, MoveInline, StayInline, TasteInline, PlayInline]


@admin.register(TripMember)
class TripMemberAdmin(admin.ModelAdmin):
    list_display = ('trip', 'user', 'role', 'joined_at')
    list_filter = ('role',)
    search_fields = ('trip__title', 'user__handle', 'user__email')


@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'status', 'check_in', 'check_out', 'total_price', 'currency')
    list_filter = ('status', 'trip')
    search_fields = ('title', 'address', 'description')


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'mode', 'status', 'departure_time', 'arrival_time', 'price')
    list_filter = ('mode', 'status', 'trip')
    search_fields = ('title', 'origin_address', 'destination_address')


@admin.register(Taste)
class TasteAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'taste_type', 'status', 'start_time', 'end_time', 'price')
    list_filter = ('status', 'taste_type', 'trip')
    search_fields = ('title', 'description', 'address')


@admin.register(Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'play_type', 'status', 'start_time', 'end_time', 'price')
    list_filter = ('status', 'play_type', 'trip')
    search_fields = ('title', 'description', 'address')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'trip', 'uploaded_by', 'created_at')
    search_fields = ('file_name', 'trip__title')


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'trip', 'resource_type', 'ip_address', 'record_hash')
    list_filter = ('action', 'resource_type')
    search_fields = ('user__handle', 'user__email', 'trip__title', 'record_hash', 'ip_address')
    readonly_fields = (
        'id', 'timestamp', 'trip', 'user', 'action', 'resource_type',
        'resource_id', 'ip_address', 'user_agent', 'metadata',
        'previous_hash', 'record_hash'
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

