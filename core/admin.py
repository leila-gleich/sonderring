from django.contrib import admin
from .models import UserProfile, Trip, TripMember, Stay, Nav, Do, Attachment, OAuthIdentity


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


class NavInline(admin.StackedInline):
    model = Nav
    extra = 0


class DoInline(admin.StackedInline):
    model = Do
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'status', 'time_granularity', 'season', 'year', 'created_by', 'created_at')
    list_filter = ('status', 'time_granularity', 'season', 'year')
    search_fields = ('title', 'location', 'description')
    inlines = [TripMemberInline, StayInline, NavInline, DoInline]


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


@admin.register(Nav)
class NavAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'mode', 'status', 'departure_time', 'arrival_time', 'price')
    list_filter = ('mode', 'status', 'trip')
    search_fields = ('title', 'origin_address', 'destination_address')


@admin.register(Do)
class DoAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'activity_type', 'status', 'start_time', 'end_time', 'price')
    list_filter = ('status', 'activity_type', 'trip')
    search_fields = ('title', 'description', 'address')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'trip', 'uploaded_by', 'created_at')
    search_fields = ('file_name', 'trip__title')
