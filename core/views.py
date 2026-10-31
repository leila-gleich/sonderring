import os
import uuid
import json
import datetime
from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, FileResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date, parse_time
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.conf import settings
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Trip, Stay, Move, Taste, Play, Nav, Do, Rec, UserProfile, TripMember, Attachment, OAuthIdentity, SecurityAuditLog, order_current_and_upcoming_trips


def get_client_ip(request):
    """Extracts client IP address from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or '127.0.0.1'


def get_safe_redirect_url(request, candidate_url=None, default='core:dashboard'):
    """Validates redirect targets against allowed hosts to prevent Open Redirect vulnerabilities."""
    raw_url = candidate_url or request.GET.get('next') or request.POST.get('next')
    if raw_url and url_has_allowed_host_and_scheme(
        url=raw_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return raw_url
    return default


def is_rate_limited(cache_key: str, max_attempts: int) -> bool:
    """Returns True if the given cache key has reached or exceeded max_attempts."""
    return cache.get(cache_key, 0) >= max_attempts


def increment_rate_limit(cache_key: str, window_seconds: int) -> int:
    """Increments a rate limit counter in cache with TTL."""
    current = cache.get(cache_key, 0) + 1
    cache.set(cache_key, current, timeout=window_seconds)
    return current


def clear_rate_limit(cache_key: str):
    """Resets a rate limit counter upon successful authentication."""
    cache.delete(cache_key)


def log_security_event(request, action, resource_type, resource_id=None, trip=None, user=None, metadata=None):
    """Records a tamper-evident SecurityAuditLog entry with SHA-256 hash chaining."""
    actor = user if user is not None else get_current_user(request)
    return SecurityAuditLog.objects.create(
        trip=trip,
        user=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        metadata=metadata or {}
    )


# ==========================================
# Authentication & Role Helpers
# ==========================================

def get_current_user(request):
    """
    Returns the currently active user stored in session, or None if unauthenticated.
    """
    user_id = request.session.get('user_id')
    if user_id:
        return UserProfile.objects.filter(id=user_id, is_active=True).first()
    return None


def login_required_profile(view_func):
    """
    Decorator requiring a valid active UserProfile in session.
    Redirects to login with a ?next= parameter if not logged in.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            login_url = reverse('core:login')
            return redirect(f"{login_url}?next={request.get_full_path()}")
        return view_func(request, *args, **kwargs)
    return _wrapped


def get_user_trip_role(user, trip):
    """
    Returns the role ('OWNER', 'EDITOR', 'VIEWER', or None) of the user on the trip.
    """
    if not user or not trip:
        return None
    if trip.created_by_id == user.id:
        return 'OWNER'
    membership = TripMember.objects.filter(trip=trip, user=user).first()
    if membership:
        return membership.role
    return None


def can_user_edit_trip(user, trip):
    """True if user is OWNER or EDITOR on the trip."""
    role = get_user_trip_role(user, trip)
    return role in ['OWNER', 'EDITOR']


def is_user_trip_owner(user, trip):
    """True if user is the OWNER of the trip."""
    return get_user_trip_role(user, trip) == 'OWNER'


def can_user_edit_item(user, trip, item):
    """
    Evaluates whether a user can edit/delete this specific itinerary item:
    Trip Owners, Editors, OR the user who personally created/uploaded the item (Universal Author Sovereignty).
    """
    if not user or not trip:
        return False
    if can_user_edit_trip(user, trip):
        return True
    if item:
        author = getattr(item, 'created_by', None) or getattr(item, 'recommended_by', None) or getattr(item, 'uploaded_by', None)
        if author and author.id == user.id:
            return True
    return False


def get_demo_users():
    """Returns active users list only when ENABLE_DEMO_SWITCHER is enabled."""
    if getattr(settings, 'ENABLE_DEMO_SWITCHER', False):
        return UserProfile.objects.filter(is_active=True).order_by('full_name')
    return UserProfile.objects.none()


# ==========================================
# Authentication & User Management Views
# ==========================================

def login_view(request):
    """
    Handles logging in via email/handle + password, or 1-click demo selection.
    """
    current_user = get_current_user(request)
    if current_user and request.method == 'GET' and not request.GET.get('switch'):
        return redirect('core:dashboard')

    all_users = get_demo_users()

    if request.method == 'POST':
        # 1. 1-Click Demo Selection (strictly gated by ENABLE_DEMO_SWITCHER)
        demo_user_id = request.POST.get('demo_user_id')
        if demo_user_id:
            if not getattr(settings, 'ENABLE_DEMO_SWITCHER', False):
                return HttpResponseForbidden("Demo login is disabled in this environment.")
            target_user = UserProfile.objects.filter(id=demo_user_id, is_active=True).first()
            if target_user:
                request.session.cycle_key()
                request.session['user_id'] = str(target_user.id)
                target_user.last_login = timezone.now()
                target_user.save(update_fields=['last_login'])
                messages.success(request, f"Welcome back, {target_user.full_name} (@{target_user.handle})!")
                return redirect(get_safe_redirect_url(request))

        # 2. Standard Email/Handle + Password verification with Brute-Force Rate Limiting
        handle_or_email = request.POST.get('handle_or_email', '').strip()
        password = request.POST.get('password', '')
        client_ip = get_client_ip(request)
        rate_key = f"ratelimit:login:{client_ip}:{handle_or_email.lower().lstrip('@')}"
        max_attempts = getattr(settings, 'LOGIN_RATE_LIMIT_ATTEMPTS', 5)
        window_seconds = getattr(settings, 'LOGIN_RATE_LIMIT_WINDOW_SECONDS', 300)

        if is_rate_limited(rate_key, max_attempts):
            messages.error(request, "Too many failed login attempts. Please wait a few minutes and try again.")
            return HttpResponse(
                render(request, 'login.html', {
                    'all_users': all_users,
                    'current_user': current_user,
                    'next': request.GET.get('next', ''),
                }).content,
                status=429
            )

        if not handle_or_email:
            messages.error(request, "Please enter your email or travel handle.")
        elif not password:
            messages.error(request, "Please enter your password.")
        else:
            clean_handle = handle_or_email.replace('@', '')
            user = UserProfile.objects.filter(
                Q(handle__iexact=clean_handle) | Q(email__iexact=handle_or_email),
                is_active=True
            ).first()

            if user and user.check_password(password):
                clear_rate_limit(rate_key)
                request.session.cycle_key()
                request.session['user_id'] = str(user.id)
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                log_security_event(
                    request,
                    action='AUTH_LOGIN_SUCCESS',
                    resource_type='USER',
                    resource_id=user.id,
                    user=user,
                    metadata={'method': 'password'}
                )
                messages.success(request, f"Welcome back, {user.full_name}!")
                return redirect(get_safe_redirect_url(request))
            else:
                increment_rate_limit(rate_key, window_seconds)
                log_security_event(
                    request,
                    action='AUTH_LOGIN_FAILED',
                    resource_type='USER',
                    resource_id=user.id if user else None,
                    user=user,
                    metadata={'attempted_identifier': handle_or_email}
                )
                messages.error(request, "Invalid email/handle or password. Please try again.")

    context = {
        'all_users': all_users,
        'current_user': current_user,
        'next': request.GET.get('next', ''),
    }
    return render(request, 'login.html', context)


def signup_view(request):
    """
    Handles user registration with full name, handle, email, and password.
    """
    current_user = get_current_user(request)
    if current_user and request.method == 'GET':
        return redirect('core:dashboard')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        handle = request.POST.get('handle', '').strip().replace('@', '').lower()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not handle:
            errors.append("A unique travel handle is required.")
        elif len(handle) < 3 or len(handle) > 30:
            errors.append("Handle must be between 3 and 30 characters.")
        elif not handle.replace('_', '').isalnum():
            errors.append("Handle can only contain letters, numbers, and underscores.")
        elif UserProfile.objects.filter(handle__iexact=handle).exists():
            errors.append(f"Handle @{handle} is already taken. Please choose another.")

        if not email:
            errors.append("Email address is required.")
        elif '@' not in email or '.' not in email.split('@')[-1]:
            errors.append("Please enter a valid email address.")
        elif UserProfile.objects.filter(email__iexact=email).exists():
            errors.append("An account with that email already exists. Please log in.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        elif password != password_confirm:
            errors.append("Passwords do not match.")
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                errors.extend(exc.messages)

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            new_user = UserProfile(
                full_name=full_name,
                handle=handle,
                email=email,
                last_login=timezone.now(),
                is_active=True
            )
            new_user.set_password(password)
            new_user.save()

            request.session.cycle_key()
            request.session['user_id'] = str(new_user.id)
            messages.success(request, f"Welcome to Sonderring, {new_user.full_name}! Your account has been created.")
            return redirect(get_safe_redirect_url(request))

    return render(request, 'signup.html', {
        'next': request.GET.get('next', ''),
        'current_user': current_user,
    })


def logout_view(request):
    """Logs out user by clearing the session."""
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('core:login')


@require_POST
def switch_user_view(request):
    """Quick 1-click user switcher from the navigation bar (dev/demo only)."""
    if not getattr(settings, 'ENABLE_DEMO_SWITCHER', False):
        return HttpResponseForbidden("Demo user switching is disabled in this environment.")

    user_id = request.POST.get('user_id')
    target_user = get_object_or_404(UserProfile, id=user_id, is_active=True)
    request.session.cycle_key()
    request.session['user_id'] = str(target_user.id)
    target_user.last_login = timezone.now()
    target_user.save(update_fields=['last_login'])
    messages.success(request, f"Switched active user to {target_user.full_name} (@{target_user.handle})")
    
    redirect_url = get_safe_redirect_url(request, candidate_url=request.META.get('HTTP_REFERER'), default='/')
    return redirect(redirect_url)


@require_POST
def change_password_view(request):
    """Allows a user to set or change their password from the profile page."""
    current_user = get_current_user(request)
    if not current_user:
        return redirect('core:login')

    old_password = request.POST.get('old_password', '')
    new_password = request.POST.get('new_password', '')
    new_password_confirm = request.POST.get('new_password_confirm', '')

    if current_user.has_usable_password():
        if not current_user.check_password(old_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('core:profile')

    if len(new_password) < 8:
        messages.error(request, "New password must be at least 8 characters long.")
        return redirect('core:profile')

    if new_password != new_password_confirm:
        messages.error(request, "New passwords do not match.")
        return redirect('core:profile')

    try:
        validate_password(new_password)
    except ValidationError as exc:
        for err in exc.messages:
            messages.error(request, err)
        return redirect('core:profile')

    current_user.set_password(new_password)
    current_user.save(update_fields=['password'])
    request.session.cycle_key()
    request.session['user_id'] = str(current_user.id)
    log_security_event(
        request,
        action='PASSWORD_CHANGED',
        resource_type='USER',
        resource_id=current_user.id,
        user=current_user
    )
    messages.success(request, "Your password has been successfully updated!")
    return redirect('core:profile')


# ==========================================
# User Profile View
# ==========================================

def profile_view(request):
    """
    Renders user profile details, editable form, and associated trips.
    """
    current_user = get_current_user(request)
    if not current_user:
        return redirect('core:login')

    all_users = get_demo_users()

    # Trips owned by the user
    owned_trips = Trip.objects.filter(created_by=current_user).order_by('-year', '-start_date')

    # Trips where the user is an invited member (and not the primary creator)
    member_trips = Trip.objects.filter(
        members__user=current_user
    ).exclude(
        created_by=current_user
    ).order_by('-year', '-start_date').distinct()

    context = {
        'current_user': current_user,
        'all_users': all_users,
        'owned_trips': owned_trips,
        'member_trips': member_trips,
    }
    return render(request, 'profile.html', context)


@require_POST
def update_profile_view(request):
    """Updates user profile information."""
    current_user = get_current_user(request)
    if not current_user:
        return redirect('core:login')

    full_name = request.POST.get('full_name', '').strip()
    handle = request.POST.get('handle', '').strip().replace('@', '').lower()
    phone_number = request.POST.get('phone_number', '').strip()
    profile_image_url = request.POST.get('profile_image_url', '').strip()

    if not full_name or not handle:
        messages.error(request, "Name and handle cannot be empty.")
        return redirect('core:profile')

    # Check if handle is taken by another user (case-insensitive)
    if UserProfile.objects.filter(handle__iexact=handle).exclude(id=current_user.id).exists():
        messages.error(request, f"Handle '@{handle}' is already in use by another traveler.")
        return redirect('core:profile')

    current_user.full_name = full_name
    current_user.handle = handle
    current_user.phone_number = phone_number
    current_user.profile_image_url = profile_image_url
    current_user.save()

    messages.success(request, "Your travel profile was successfully updated!")
    return redirect('core:profile')


# ==========================================
# Dashboard & Trip Workspace Views
# ==========================================

def dashboard_view(request):
    """
    Renders the main TripSpace dashboard with upcoming, active, and past trips.
    Strictly scoped to trips created by the user or where the user is an invited member.
    """
    current_user = get_current_user(request)
    if not current_user:
        login_url = reverse('core:login')
        return redirect(f"{login_url}?next={request.path}")

    all_users = get_demo_users()
    
    # Scoped strictly to trips the current user created or belongs to as a tripper
    user_trips = Trip.objects.filter(
        Q(created_by=current_user) | Q(members__user=current_user)
    ).distinct()

    # Categorize TripSpaces by Current/Upcoming vs Past
    # For Current & Upcoming Trips: CURRENT is first (farthest left), then chronological order
    upcoming_trips = order_current_and_upcoming_trips(user_trips)
    past_trips = user_trips.filter(status='PAST').order_by('-year', '-start_date')

    editable_trip_ids = set(
        user_trips.filter(
            Q(created_by=current_user) | Q(members__user=current_user, members__role__in=['OWNER', 'EDITOR'])
        ).values_list('id', flat=True)
    )

    context = {
        'current_user': current_user,
        'all_users': all_users,
        'upcoming_trips': upcoming_trips,
        'past_trips': past_trips,
        'editable_trip_ids': editable_trip_ids,
        'now_year': timezone.now().year,
    }
    return render(request, 'dashboard.html', context)


def trip_workspace_view(request, trip_id):
    """
    Renders the dedicated workspace for a single trip with tabbed navigation:
    Timeline/Itinerary, Stays, Navs, Dos & Recs, and Vault.
    Includes full role-based permissions (Owner vs Editor vs Viewer).
    Blocks unauthorized access if user is not creator or member.
    """
    current_user = get_current_user(request)
    if not current_user:
        login_url = reverse('core:login')
        return redirect(f"{login_url}?next={request.path}")

    all_users = get_demo_users()
    trip = get_object_or_404(Trip, id=trip_id)

    # Determine user role on this specific trip
    user_role = get_user_trip_role(current_user, trip)
    if not user_role:
        messages.error(request, "You do not have permission to access this trip space.")
        return redirect('core:dashboard')

    is_owner = (user_role == 'OWNER')
    is_editor = (user_role in ['OWNER', 'EDITOR'])
    is_viewer = (user_role == 'VIEWER')
    can_edit = is_editor

    moves = trip.moves.select_related('created_by', 'updated_by').all().order_by('departure_time', 'created_at')
    stays = trip.stays.select_related('created_by', 'updated_by').prefetch_related('attachments').all().order_by('check_in', 'created_at')
    tastes = trip.tastes.select_related('recommended_by', 'created_by', 'updated_by').all().order_by('start_time', 'created_at')
    plays = trip.plays.select_related('recommended_by', 'created_by', 'updated_by').all().order_by('start_time', 'created_at')
    attachments = trip.attachments.select_related('move', 'stay', 'taste', 'play', 'uploaded_by', 'updated_by').all().order_by('-created_at')
    members = trip.members.select_related('user').all()

    # Moves grouped by stage
    moves_start_end = [m for m in moves if m.trip_stage == 'START_END']
    moves_mid_trip = [m for m in moves if m.trip_stage == 'MID_TRIP']

    # Combined Chronological Timeline Items (Move, Stay, Taste, Play)
    timeline_items = []
    for m in moves:
        move_location = None
        if m.origin_address and m.destination_address:
            move_location = f"{m.origin_address} ➔ {m.destination_address}"
        elif m.origin_address:
            move_location = m.origin_address
        elif m.destination_address:
            move_location = m.destination_address

        timeline_items.append({
            'type': 'move',
            'id': str(m.id),
            'title': m.title,
            'subtitle': f"{m.mode} ({m.get_direction_display() if hasattr(m, 'get_direction_display') else m.direction})",
            'location': move_location,
            'status': m.status,
            'timestamp': m.departure_time,
            'end_timestamp': None,
            'has_time': m.is_departure_time_set,
            'has_end_time': False,
            'price': m.price,
            'currency': m.currency,
            'has_code': m.has_confirmation_code,
            'obj': m,
        })

    for s in stays:
        timeline_items.append({
            'type': 'stay',
            'id': str(s.id),
            'title': s.title,
            'subtitle': s.place_type or 'Accommodation',
            'location': s.address,
            'status': s.status,
            'timestamp': s.check_in,
            'end_timestamp': s.check_out,
            'has_time': s.is_check_in_time_set,
            'has_end_time': s.is_check_out_time_set,
            'price': s.total_price,
            'currency': s.currency,
            'has_code': s.has_confirmation_code,
            'obj': s,
        })

    for t in tastes:
        timeline_items.append({
            'type': 'taste',
            'id': str(t.id),
            'title': t.title,
            'subtitle': t.get_taste_type_display() if hasattr(t, 'get_taste_type_display') else t.taste_type,
            'location': t.address,
            'status': t.status,
            'timestamp': t.start_time,
            'end_timestamp': None,
            'has_time': t.is_start_time_set,
            'has_end_time': False,
            'price': t.price,
            'currency': t.currency,
            'has_code': t.has_confirmation_code,
            'obj': t,
        })

    for p in plays:
        timeline_items.append({
            'type': 'play',
            'id': str(p.id),
            'title': p.title,
            'subtitle': p.get_play_type_display() if hasattr(p, 'get_play_type_display') else p.play_type,
            'location': p.address,
            'status': p.status,
            'timestamp': p.start_time,
            'end_timestamp': None,
            'has_time': p.is_start_time_set,
            'has_end_time': False,
            'price': p.price,
            'currency': p.currency,
            'has_code': p.has_confirmation_code,
            'obj': p,
        })

    # Sort timeline: dated items first chronologically, undated items at end
    timeline_items.sort(
        key=lambda item: (
            0 if item['timestamp'] is not None else 1,
            item['timestamp'] or timezone.now()
        )
    )

    # Financial totals across all elements (include both CONFIRMED and COMPLETE items)
    total_spend = (
        sum(float(m.price or 0) for m in moves if m.status in ('CONFIRMED', 'COMPLETE')) +
        sum(float(s.total_price or 0) for s in stays if s.status in ('CONFIRMED', 'COMPLETE')) +
        sum(float(t.price or 0) for t in tastes if t.status in ('CONFIRMED', 'COMPLETE')) +
        sum(float(p.price or 0) for p in plays if p.status in ('CONFIRMED', 'COMPLETE'))
    )

    context = {
        'current_user': current_user,
        'all_users': all_users,
        'trip': trip,
        'user_role': user_role,
        'is_owner': is_owner,
        'is_editor': is_editor,
        'is_viewer': is_viewer,
        'can_edit': can_edit,
        'moves': moves,
        'stays': stays,
        'tastes': tastes,
        'plays': plays,
        'moves_start_end': moves_start_end,
        'moves_mid_trip': moves_mid_trip,
        # Legacy aliases
        'navs': moves,
        'navs_start_end': moves_start_end,
        'navs_mid_trip': moves_mid_trip,
        'dos': plays,
        'recs': tastes,
        'attachments': attachments,
        'members': members,
        'timeline_items': timeline_items,
        'total_spend': total_spend,
        'available_users': get_demo_users().exclude(trip_memberships__trip=trip),
    }
    return render(request, 'trip_workspace.html', context)


# ==========================================
# Trip CRUD Operations
# ==========================================

@require_POST
def create_trip_view(request):
    """Creates a new Trip record supporting all 4 hybrid time granularities."""
    current_user = get_current_user(request)
    if not current_user:
        return redirect(f"{reverse('core:login')}?next={request.path}")
    
    title = request.POST.get('title', '').strip()
    location = request.POST.get('location', '').strip()
    description = request.POST.get('description', '').strip()
    time_granularity = request.POST.get('time_granularity', 'YEAR')
    trip_status = request.POST.get('status', 'UPCOMING').strip().upper()
    if trip_status not in ['UPCOMING', 'CURRENT', 'PAST']:
        trip_status = 'UPCOMING'
    
    if not title or not location:
        messages.error(request, "Trip title and location are required.")
        return redirect('core:dashboard')

    trip_data = {
        'title': title,
        'location': location,
        'description': description,
        'status': trip_status,
        'time_granularity': time_granularity,
        'created_by': current_user,
    }
    ############ TIME GRANULARITY ###########
    if time_granularity == 'EXACT_RANGE':
        s_date = request.POST.get('start_date')
        e_date = request.POST.get('end_date')
        if s_date and e_date:
            parsed_s = parse_date(s_date)
            parsed_e = parse_date(e_date)
            if parsed_s and parsed_e and parsed_e < parsed_s:
                messages.error(request, "Trip end date cannot be before start date.")
                return redirect('core:dashboard')
            trip_data['start_date'] = parsed_s
            trip_data['end_date'] = parsed_e
            trip_data['year'] = trip_data['start_date'].year if trip_data['start_date'] else timezone.now().year
    
    elif time_granularity == 'SEASON_YEAR':
        trip_data['season'] = request.POST.get('season', 'SUMMER')
        trip_data['year'] = int(request.POST.get('season_year') or timezone.now().year)
    
    elif time_granularity == 'MONTH':
        trip_data['start_month'] = int(request.POST.get('start_month') or 1)
        end_m = request.POST.get('end_month')
        if end_m:
            trip_data['end_month'] = int(end_m)
        trip_data['year'] = int(request.POST.get('month_year') or timezone.now().year)
    
    else: # YEAR
        trip_data['year'] = int(request.POST.get('year') or timezone.now().year)

    trip = Trip.objects.create(**trip_data)
    
    # Automatically add creator as OWNER
    TripMember.objects.create(trip=trip, user=current_user, role='OWNER')
    
    messages.success(request, f"Trip '{trip.title}' created successfully!")
    return redirect('core:trip_workspace', trip_id=trip.id)


@require_POST
def edit_trip_view(request, trip_id):
    """Updates high-level trip metadata (title, location, description, dates)."""
    current_user = get_current_user(request)
    trip = get_object_or_404(Trip, id=trip_id)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Only Owners and Editors can update this trip.")
        return redirect('core:trip_workspace', trip_id=trip.id)

    title = request.POST.get('title', '').strip()
    location = request.POST.get('location', '').strip()
    description = request.POST.get('description', '').strip()
    time_granularity = request.POST.get('time_granularity', trip.time_granularity)
    new_status = request.POST.get('status', trip.status).strip().upper()

    if not title or not location:
        messages.error(request, "Trip title and location cannot be blank.")
        return redirect('core:trip_workspace', trip_id=trip.id)

    trip.title = title
    trip.location = location
    trip.description = description
    trip.time_granularity = time_granularity
    if new_status in ['UPCOMING', 'CURRENT', 'PAST']:
        trip.status = new_status

    if time_granularity == 'EXACT_RANGE':
        s_date = request.POST.get('start_date')
        e_date = request.POST.get('end_date')
        parsed_s = parse_date(s_date) if s_date else None
        parsed_e = parse_date(e_date) if e_date else None
        if parsed_s and parsed_e and parsed_e < parsed_s:
            messages.error(request, "Trip end date cannot be before start date.")
            return redirect('core:trip_workspace', trip_id=trip.id)
        trip.start_date = parsed_s
        trip.end_date = parsed_e
        if trip.start_date:
            trip.year = trip.start_date.year
    elif time_granularity == 'SEASON_YEAR':
        trip.season = request.POST.get('season', 'SUMMER')
        trip.year = int(request.POST.get('season_year') or timezone.now().year)
    elif time_granularity == 'MONTH':
        trip.start_month = int(request.POST.get('start_month') or 1)
        end_m = request.POST.get('end_month')
        trip.end_month = int(end_m) if end_m else None
        trip.year = int(request.POST.get('month_year') or timezone.now().year)
    else: # YEAR
        trip.year = int(request.POST.get('year') or timezone.now().year)

    trip.updated_by = current_user
    trip.save()
    messages.success(request, f"Trip '{trip.title}' details updated successfully!")
    return redirect('core:trip_workspace', trip_id=trip.id)


@require_POST
def update_trip_status_view(request, trip_id):
    """Updates a TripSpace's status (UPCOMING, CURRENT, PAST) directly."""
    current_user = get_current_user(request)
    trip = get_object_or_404(Trip, id=trip_id)

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('accept', '')
    )
    redirect_fallback = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('core:trip_workspace', args=[trip.id])

    if not can_user_edit_trip(current_user, trip):
        if is_ajax:
            return HttpResponseForbidden("Only Trip Owners and Editors can change trip status.")
        messages.error(request, "Permission denied: Only Owners and Editors can change trip status.")
        return redirect(redirect_fallback)

    new_status = request.POST.get('status', '').strip().upper()
    if new_status not in ['UPCOMING', 'CURRENT', 'PAST']:
        if is_ajax:
            return HttpResponseBadRequest("Invalid trip status. Must be UPCOMING, CURRENT, or PAST.")
        messages.error(request, "Invalid trip status selected.")
        return redirect(redirect_fallback)

    trip.status = new_status
    trip.updated_by = current_user
    trip.save()

    label = trip.get_status_display()

    if is_ajax:
        return JsonResponse({
            'success': True,
            'trip_id': str(trip.id),
            'new_status': trip.status,
            'status_display': label,
        })

    messages.success(request, f"Trip '{trip.title}' status updated to {label}!")
    return redirect(redirect_fallback)


@require_POST
def delete_trip_view(request, trip_id):
    """Deletes a trip. Restricted strictly to the Trip OWNER."""
    current_user = get_current_user(request)
    trip = get_object_or_404(Trip, id=trip_id)

    if not is_user_trip_owner(current_user, trip):
        messages.error(request, "Permission denied: Only the Trip Owner can permanently delete this TripSpace.")
        return redirect('core:trip_workspace', trip_id=trip.id)

    trip_title = trip.title
    trip.delete()
    messages.success(request, f"Trip '{trip_title}' was permanently deleted.")
    return redirect('core:dashboard')


# ==========================================
# Stay CRUD Operations
# ==========================================

def _normalize_item_status(raw_status, default='IDEA') -> str:
    val = (raw_status or default).strip().upper()
    return val if val in ('IDEA', 'CONFIRMED', 'COMPLETE') else default


def _parse_stay_datetimes(request):
    """
    Parses check_in and check_out dates and optional times from request.POST.
    Supports both separated date/time fields (check_in_date, check_in_time, check_out_date, check_out_time)
    and legacy combined datetime fields (check_in, check_out).
    Returns (check_in_dt, check_out_dt, has_ci_time, has_co_time).
    """
    ci_date_raw = request.POST.get('check_in_date', '').strip()
    ci_time_raw = request.POST.get('check_in_time', '').strip()
    co_date_raw = request.POST.get('check_out_date', '').strip()
    co_time_raw = request.POST.get('check_out_time', '').strip()

    check_in_raw = request.POST.get('check_in', '').strip()
    check_out_raw = request.POST.get('check_out', '').strip()

    check_in_dt = None
    has_ci_time = False
    if ci_date_raw:
        d = parse_date(ci_date_raw)
        if d:
            if ci_time_raw:
                t = parse_time(ci_time_raw)
                if t is None:
                    try:
                        parts = [int(p) for p in ci_time_raw.split(':')]
                        t = datetime.time(parts[0], parts[1])
                    except Exception:
                        t = datetime.time(0, 0)
                combined = datetime.datetime.combine(d, t)
                check_in_dt = timezone.make_aware(combined) if settings.USE_TZ else combined
                has_ci_time = True
            else:
                combined = datetime.datetime.combine(d, datetime.time(0, 0))
                check_in_dt = timezone.make_aware(combined) if settings.USE_TZ else combined
                has_ci_time = False
    elif check_in_raw:
        dt = parse_datetime(check_in_raw)
        if dt:
            if settings.USE_TZ and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            check_in_dt = dt
            has_ci_time = not (dt.hour == 0 and dt.minute == 0)

    check_out_dt = None
    has_co_time = False
    if co_date_raw:
        d = parse_date(co_date_raw)
        if d:
            if co_time_raw:
                t = parse_time(co_time_raw)
                if t is None:
                    try:
                        parts = [int(p) for p in co_time_raw.split(':')]
                        t = datetime.time(parts[0], parts[1])
                    except Exception:
                        t = datetime.time(0, 0)
                combined = datetime.datetime.combine(d, t)
                check_out_dt = timezone.make_aware(combined) if settings.USE_TZ else combined
                has_co_time = True
            else:
                combined = datetime.datetime.combine(d, datetime.time(0, 0))
                check_out_dt = timezone.make_aware(combined) if settings.USE_TZ else combined
                has_co_time = False
    elif check_out_raw:
        dt = parse_datetime(check_out_raw)
        if dt:
            if settings.USE_TZ and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            check_out_dt = dt
            has_co_time = not (dt.hour == 0 and dt.minute == 0)

    return check_in_dt, check_out_dt, has_ci_time, has_co_time


def _parse_element_datetime(request, date_names=('date',), time_names=('time',), legacy_names=()):
    """
    Parses a single date and optional time from request.POST for Move, Taste, or Play.
    Supports:
      1. Separated date and optional time fields (e.g. date + time)
      2. Legacy combined datetime/date field (e.g. departure_time or start_time)
    Returns (dt, has_time).
    """
    date_raw = ''
    for dn in date_names:
        val = request.POST.get(dn, '').strip()
        if val:
            date_raw = val
            break

    time_raw = ''
    for tn in time_names:
        val = request.POST.get(tn, '').strip()
        if val:
            time_raw = val
            break

    legacy_raw = ''
    for ln in legacy_names:
        val = request.POST.get(ln, '').strip()
        if val:
            legacy_raw = val
            break

    dt = None
    has_time = False

    if date_raw:
        d = parse_date(date_raw)
        if d:
            if time_raw:
                t = parse_time(time_raw)
                if t is None:
                    try:
                        parts = [int(p) for p in time_raw.split(':')]
                        t = datetime.time(parts[0], parts[1])
                    except Exception:
                        t = datetime.time(0, 0)
                combined = datetime.datetime.combine(d, t)
                dt = timezone.make_aware(combined) if settings.USE_TZ else combined
                has_time = True
            else:
                combined = datetime.datetime.combine(d, datetime.time(0, 0))
                dt = timezone.make_aware(combined) if settings.USE_TZ else combined
                has_time = False
    elif legacy_raw:
        parsed_dt = parse_datetime(legacy_raw)
        if parsed_dt:
            if settings.USE_TZ and timezone.is_naive(parsed_dt):
                parsed_dt = timezone.make_aware(parsed_dt)
            dt = parsed_dt
            has_time = not (parsed_dt.hour == 0 and parsed_dt.minute == 0)
        else:
            d = parse_date(legacy_raw)
            if d:
                combined = datetime.datetime.combine(d, datetime.time(0, 0))
                dt = timezone.make_aware(combined) if settings.USE_TZ else combined
                has_time = False

    return dt, has_time


@require_POST
def add_stay_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Only Trip Owners and Editors can add accommodations.")
        return redirect(f"/trips/{trip_id}/#stays")

    title = request.POST.get('title', '').strip()
    if not title:
        messages.error(request, "Stay name is required.")
        return redirect(f"/trips/{trip_id}/#stays")

    status = _normalize_item_status(request.POST.get('status'), 'IDEA')
    check_in_dt, check_out_dt, has_ci_time, has_co_time = _parse_stay_datetimes(request)

    if status == 'CONFIRMED':
        if not check_in_dt or not check_out_dt:
            messages.error(request, "Confirmed stays require both a check-in date (start) and check-out date (end).")
            return redirect(f"/trips/{trip_id}/#stays")

    if check_in_dt and check_out_dt and check_out_dt < check_in_dt:
        messages.error(request, "Check-out date/time cannot be before check-in date/time.")
        return redirect(f"/trips/{trip_id}/#stays")

    stay = Stay(
        trip=trip,
        title=title,
        status=status,
        place_type=request.POST.get('place_type', 'Hotel Room') or 'Hotel Room',
        num_beds=int(request.POST.get('num_beds')) if request.POST.get('num_beds') else None,
        num_rooms=int(request.POST.get('num_rooms')) if request.POST.get('num_rooms') else None,
        num_guests=int(request.POST.get('num_guests')) if request.POST.get('num_guests') else None,
        address=request.POST.get('address', '').strip(),
        check_in=check_in_dt,
        check_out=check_out_dt,
        has_check_in_time=has_ci_time,
        has_check_out_time=has_co_time,
        total_price=float(request.POST.get('total_price')) if request.POST.get('total_price') else None,
        currency=request.POST.get('currency', 'USD'),
        booking_link=request.POST.get('booking_link', '').strip(),
        notes=request.POST.get('notes', '').strip(),
        created_by=current_user,
        updated_by=current_user
    )

    code = request.POST.get('confirmation_code', '').strip()
    is_confirmed_hotel = (status == 'CONFIRMED' and 'hotel' in (stay.place_type or '').lower())
    if code and is_confirmed_hotel:
        stay.confirmation_code = code

    stay.save()

    # Process attached documents
    uploaded_files = request.FILES.getlist('documents') or request.FILES.getlist('document') or request.FILES.getlist('file')
    uploaded_count = 0
    for file_obj in uploaded_files:
        if not file_obj:
            continue
        is_valid, err_msg, detected_mime, safe_ext = validate_and_sanitize_vault_file(file_obj)
        if not is_valid:
            messages.warning(request, f"Document '{file_obj.name}' skipped: {err_msg}")
            continue

        orig_filename = sanitize_display_filename(file_obj.name or 'Document')
        randomized_name = f"{uuid.uuid4().hex}{safe_ext}"
        file_obj.name = randomized_name
        storage_path = f"vault/{trip.id}/{randomized_name}"

        attachment = Attachment.objects.create(
            trip=trip,
            stay=stay,
            file_name=orig_filename,
            file_type=detected_mime,
            file=file_obj,
            storage_path=storage_path,
            uploaded_by=current_user,
            updated_by=current_user
        )
        log_security_event(
            request,
            action='VAULT_DOCUMENT_UPLOADED',
            resource_type='ATTACHMENT',
            resource_id=attachment.id,
            trip=trip,
            user=current_user,
            metadata={'file_name': attachment.file_name, 'file_type': attachment.file_type, 'stay_id': str(stay.id)}
        )
        uploaded_count += 1

    if uploaded_count > 0:
        messages.success(request, f"Stay '{stay.title}' added with {uploaded_count} uploaded document{'s' if uploaded_count > 1 else ''}!")
    else:
        messages.success(request, f"Stay '{stay.title}' added successfully!")
    return redirect(f"/trips/{trip_id}/#stays")


@require_POST
def edit_stay_view(request, trip_id, stay_id):
    trip = get_object_or_404(Trip, id=trip_id)
    stay = get_object_or_404(Stay, id=stay_id, trip=trip)
    current_user = get_current_user(request)

    next_url = request.POST.get('next')
    fallback_redirect = next_url if (next_url and next_url.startswith('/')) else f"/trips/{trip_id}/#stays"

    if not can_user_edit_item(current_user, trip, stay):
        messages.error(request, "Permission denied: You can only edit accommodations you created or if you are a Trip Editor/Owner.")
        return redirect(fallback_redirect)

    new_title = request.POST.get('title', stay.title).strip()
    if not new_title:
        messages.error(request, "Stay title cannot be blank.")
        return redirect(fallback_redirect)

    new_status = _normalize_item_status(request.POST.get('status'), stay.status)
    dates_in_form = ('check_in_date' in request.POST or 'check_in' in request.POST or 
                     'check_out_date' in request.POST or 'check_out' in request.POST)

    if dates_in_form:
        check_in_dt, check_out_dt, has_ci_time, has_co_time = _parse_stay_datetimes(request)
        if new_status == 'CONFIRMED' and (not check_in_dt or not check_out_dt):
            messages.error(request, "Confirmed stays require both a check-in date (start) and check-out date (end).")
            return redirect(fallback_redirect)

        if check_in_dt and check_out_dt and check_out_dt < check_in_dt:
            messages.error(request, "Check-out date/time cannot be before check-in date/time.")
            return redirect(fallback_redirect)

        stay.check_in = check_in_dt
        stay.check_out = check_out_dt
        stay.has_check_in_time = has_ci_time
        stay.has_check_out_time = has_co_time
    else:
        if new_status == 'CONFIRMED' and (not stay.check_in or not stay.check_out):
            messages.error(request, "Confirmed stays require both a check-in date (start) and check-out date (end).")
            return redirect(fallback_redirect)

    stay.title = new_title
    stay.status = new_status
    stay.place_type = request.POST.get('place_type', stay.place_type)
    stay.num_beds = int(request.POST.get('num_beds')) if request.POST.get('num_beds') else None
    stay.num_rooms = int(request.POST.get('num_rooms')) if request.POST.get('num_rooms') else None
    stay.num_guests = int(request.POST.get('num_guests')) if request.POST.get('num_guests') else None
    stay.address = request.POST.get('address', '').strip()
    
    stay.total_price = float(request.POST.get('total_price')) if request.POST.get('total_price') else None
    stay.currency = request.POST.get('currency', stay.currency)
    stay.booking_link = request.POST.get('booking_link', '').strip()
    stay.notes = request.POST.get('notes', '').strip()

    code = request.POST.get('confirmation_code', '').strip()
    if code:
        stay.confirmation_code = code

    stay.updated_by = current_user
    stay.save()

    # Process attached documents
    uploaded_files = request.FILES.getlist('documents') or request.FILES.getlist('document') or request.FILES.getlist('file')
    uploaded_count = 0
    for file_obj in uploaded_files:
        if not file_obj:
            continue
        is_valid, err_msg, detected_mime, safe_ext = validate_and_sanitize_vault_file(file_obj)
        if not is_valid:
            messages.warning(request, f"Document '{file_obj.name}' skipped: {err_msg}")
            continue

        orig_filename = sanitize_display_filename(file_obj.name or 'Document')
        randomized_name = f"{uuid.uuid4().hex}{safe_ext}"
        file_obj.name = randomized_name
        storage_path = f"vault/{trip.id}/{randomized_name}"

        attachment = Attachment.objects.create(
            trip=trip,
            stay=stay,
            file_name=orig_filename,
            file_type=detected_mime,
            file=file_obj,
            storage_path=storage_path,
            uploaded_by=current_user,
            updated_by=current_user
        )
        log_security_event(
            request,
            action='VAULT_DOCUMENT_UPLOADED',
            resource_type='ATTACHMENT',
            resource_id=attachment.id,
            trip=trip,
            user=current_user,
            metadata={'file_name': attachment.file_name, 'file_type': attachment.file_type, 'stay_id': str(stay.id)}
        )
        uploaded_count += 1

    if uploaded_count > 0:
        messages.success(request, f"Updated Stay '{stay.title}' with {uploaded_count} new document{'s' if uploaded_count > 1 else ''}!")
    else:
        messages.success(request, f"Updated Stay '{stay.title}'!")
    return redirect(fallback_redirect)


@require_POST
def delete_stay_view(request, trip_id, stay_id):
    trip = get_object_or_404(Trip, id=trip_id)
    stay = get_object_or_404(Stay, id=stay_id, trip=trip)
    current_user = get_current_user(request)

    if not can_user_edit_item(current_user, trip, stay):
        messages.error(request, "Permission denied: You can only delete accommodations you created or if you are a Trip Editor/Owner.")
        return redirect(f"/trips/{trip_id}/#stays")

    title = stay.title
    stay.delete()
    messages.success(request, f"Stay '{title}' deleted.")
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#stays")


# ==========================================
# Move CRUD Operations
# ==========================================

@require_POST
def add_move_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Only Trip Owners and Editors can add transportation legs.")
        return redirect(f"/trips/{trip_id}/#move")

    title = request.POST.get('title', '').strip()
    mode = request.POST.get('mode', 'Flight')
    if not title:
        messages.error(request, "Transit leg name is required.")
        return redirect(f"/trips/{trip_id}/#move")

    dept_dt, has_dept_time = _parse_element_datetime(
        request,
        date_names=('date', 'departure_date'),
        time_names=('time', 'departure_time_only'),
        legacy_names=('departure_time',)
    )
    status = _normalize_item_status(request.POST.get('status'), 'IDEA')

    if status == 'CONFIRMED' and not dept_dt:
        messages.error(request, "Confirmed moves require a date.")
        return redirect(f"/trips/{trip_id}/#move")

    # If legacy tests explicitly pass arrival_time, ensure chronological order if present
    arr_raw = request.POST.get('arrival_time')
    arr_dt = parse_datetime(arr_raw) if arr_raw else None
    if arr_dt and settings.USE_TZ and timezone.is_naive(arr_dt):
        arr_dt = timezone.make_aware(arr_dt)
    if dept_dt and arr_dt and arr_dt < dept_dt:
        messages.error(request, "Arrival date/time cannot be before departure date/time.")
        return redirect(f"/trips/{trip_id}/#move")

    move = Move(
        trip=trip,
        title=title,
        mode=mode,
        trip_stage=request.POST.get('trip_stage', 'START_END'),
        direction=request.POST.get('direction', 'ARRIVING'),
        status=status,
        passenger_name=request.POST.get('passenger_name', '').strip(),
        origin_address=request.POST.get('origin_address', '').strip(),
        destination_address=request.POST.get('destination_address', '').strip(),
        departure_time=dept_dt,
        arrival_time=None,
        has_departure_time=has_dept_time,
        has_arrival_time=False,
        date_confidence=request.POST.get('date_confidence', 'CONFIRMED'),
        time_confidence=request.POST.get('time_confidence', 'CONFIRMED'),
        flexibility_notes=request.POST.get('flexibility_notes', '').strip(),
        price=float(request.POST.get('price')) if request.POST.get('price') else None,
        currency=request.POST.get('currency', 'USD'),
        booking_link=request.POST.get('booking_link', '').strip(),
        created_by=current_user,
        updated_by=current_user
    )

    code = request.POST.get('confirmation_code', '').strip()
    if code:
        move.confirmation_code = code

    move.save()
    messages.success(request, f"Transit leg '{move.title}' added successfully!")
    return redirect(f"/trips/{trip_id}/#move")


@require_POST
def edit_move_view(request, trip_id, move_id):
    trip = get_object_or_404(Trip, id=trip_id)
    move = get_object_or_404(Move, id=move_id, trip=trip)
    current_user = get_current_user(request)

    next_url = request.POST.get('next')
    fallback_redirect = next_url if (next_url and next_url.startswith('/')) else f"/trips/{trip_id}/#move"

    if not can_user_edit_item(current_user, trip, move):
        messages.error(request, "Permission denied: You can only edit transportation legs you created or if you are a Trip Editor/Owner.")
        return redirect(fallback_redirect)

    new_status = _normalize_item_status(request.POST.get('status'), move.status)
    dates_in_form = any(k in request.POST for k in ('date', 'departure_date', 'departure_time'))

    if dates_in_form:
        dept_dt, has_dept_time = _parse_element_datetime(
            request,
            date_names=('date', 'departure_date'),
            time_names=('time', 'departure_time_only'),
            legacy_names=('departure_time',)
        )
        if new_status == 'CONFIRMED' and not dept_dt:
            messages.error(request, "Confirmed moves require a date.")
            return redirect(fallback_redirect)

        arr_raw = request.POST.get('arrival_time')
        arr_dt = parse_datetime(arr_raw) if arr_raw else None
        if arr_dt and settings.USE_TZ and timezone.is_naive(arr_dt):
            arr_dt = timezone.make_aware(arr_dt)
        if dept_dt and arr_dt and arr_dt < dept_dt:
            messages.error(request, "Arrival date/time cannot be before departure date/time.")
            return redirect(fallback_redirect)

        move.departure_time = dept_dt
        move.has_departure_time = has_dept_time
    else:
        if new_status == 'CONFIRMED' and not move.departure_time:
            messages.error(request, "Confirmed moves require a date.")
            return redirect(fallback_redirect)

    move.title = request.POST.get('title', move.title).strip()
    move.mode = request.POST.get('mode', move.mode)
    move.trip_stage = request.POST.get('trip_stage', move.trip_stage)
    move.direction = request.POST.get('direction', move.direction)
    move.status = new_status
    move.passenger_name = request.POST.get('passenger_name', '').strip()
    move.origin_address = request.POST.get('origin_address', '').strip()
    move.destination_address = request.POST.get('destination_address', '').strip()
    move.arrival_time = None
    move.has_arrival_time = False

    move.date_confidence = request.POST.get('date_confidence', move.date_confidence)
    move.time_confidence = request.POST.get('time_confidence', move.time_confidence)
    move.flexibility_notes = request.POST.get('flexibility_notes', '').strip()
    move.price = float(request.POST.get('price')) if request.POST.get('price') else None
    move.currency = request.POST.get('currency', move.currency)
    move.booking_link = request.POST.get('booking_link', '').strip()

    code = request.POST.get('confirmation_code', '').strip()
    if code:
        move.confirmation_code = code

    move.updated_by = current_user
    move.save()
    messages.success(request, f"Updated Transit Leg '{move.title}'!")
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#move")


@require_POST
def delete_move_view(request, trip_id, move_id):
    trip = get_object_or_404(Trip, id=trip_id)
    move = get_object_or_404(Move, id=move_id, trip=trip)
    current_user = get_current_user(request)

    if not can_user_edit_item(current_user, trip, move):
        messages.error(request, "Permission denied: You can only delete transportation legs you created or if you are a Trip Editor/Owner.")
        return redirect(f"/trips/{trip_id}/#move")

    title = move.title
    move.delete()
    messages.success(request, f"Transit leg '{title}' deleted.")
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#move")


# Backward compatibility aliases for Nav
add_nav_view = add_move_view
edit_nav_view = edit_move_view
delete_nav_view = delete_move_view


# ==========================================
# Taste CRUD Operations (Food & Drink)
# ==========================================

@require_POST
def add_taste_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Only Trip Owners and Editors can add food & drink spots.")
        return redirect(f"/trips/{trip_id}/#taste")

    title = (request.POST.get('name') or request.POST.get('title', '')).strip()
    if not title:
        messages.error(request, "Food & drink title is required.")
        return redirect(f"/trips/{trip_id}/#taste")

    status = _normalize_item_status(request.POST.get('status'), 'IDEA')
    taste_dt, has_taste_time = _parse_element_datetime(
        request,
        date_names=('date', 'taste_date'),
        time_names=('time', 'taste_time'),
        legacy_names=('start_time',)
    )

    if status == 'CONFIRMED' and not taste_dt:
        messages.error(request, "Confirmed food & drink reservations require a date.")
        return redirect(f"/trips/{trip_id}/#taste")

    e_time = request.POST.get('end_time')
    end_dt = parse_datetime(e_time) if e_time else None
    if end_dt and settings.USE_TZ and timezone.is_naive(end_dt):
        end_dt = timezone.make_aware(end_dt)
    if taste_dt and end_dt and end_dt < taste_dt:
        messages.error(request, "End date/time cannot be before start date/time.")
        return redirect(f"/trips/{trip_id}/#taste")

    raw_price = request.POST.get('price')
    try:
        price_val = float(raw_price) if raw_price else None
    except (ValueError, TypeError):
        price_val = None

    taste_type = request.POST.get('category') or request.POST.get('taste_type', 'Food')
    price_range = request.POST.get('price_range', '').strip() or None
    menu_link = (request.POST.get('menu_link') or request.POST.get('link', '')).strip() or None
    general_link = request.POST.get('general_link', '').strip() or None

    taste = Taste(
        trip=trip,
        title=title,
        taste_type=taste_type,
        status=status,
        address=request.POST.get('address', '').strip(),
        start_time=taste_dt,
        end_time=None,
        has_start_time=has_taste_time,
        has_end_time=False,
        price=price_val,
        price_range=price_range,
        currency=request.POST.get('currency', 'USD'),
        link=menu_link,
        menu_link=menu_link,
        general_link=general_link,
        description=request.POST.get('description', '').strip(),
        notes=request.POST.get('notes', '').strip(),
        created_by=current_user,
        updated_by=current_user
    )

    code = request.POST.get('confirmation_code', '').strip()
    if code:
        taste.confirmation_code = code

    taste.save()
    messages.success(request, f"Taste '{taste.title}' added successfully!")
    return redirect(f"/trips/{trip_id}/#taste")


@require_POST
def edit_taste_view(request, trip_id, taste_id):
    trip = get_object_or_404(Trip, id=trip_id)
    taste = get_object_or_404(Taste, id=taste_id, trip=trip)
    current_user = get_current_user(request)

    next_url = request.POST.get('next')
    fallback_redirect = next_url if (next_url and next_url.startswith('/')) else f"/trips/{trip_id}/#taste"

    if not can_user_edit_item(current_user, trip, taste):
        messages.error(request, "Permission denied: You can only edit dining spots you created or if you are a Trip Editor/Owner.")
        return redirect(fallback_redirect)

    new_status = _normalize_item_status(request.POST.get('status'), taste.status)
    dates_in_form = any(k in request.POST for k in ('date', 'taste_date', 'start_time'))

    if dates_in_form:
        taste_dt, has_taste_time = _parse_element_datetime(
            request,
            date_names=('date', 'taste_date'),
            time_names=('time', 'taste_time'),
            legacy_names=('start_time',)
        )
        if new_status == 'CONFIRMED' and not taste_dt:
            messages.error(request, "Confirmed food & drink reservations require a date.")
            return redirect(fallback_redirect)

        e_time = request.POST.get('end_time')
        end_dt = parse_datetime(e_time) if e_time else None
        if end_dt and settings.USE_TZ and timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)
        if taste_dt and end_dt and end_dt < taste_dt:
            messages.error(request, "End date/time cannot be before start date/time.")
            return redirect(fallback_redirect)

        taste.start_time = taste_dt
        taste.has_start_time = has_taste_time
    else:
        if new_status == 'CONFIRMED' and not taste.start_time:
            messages.error(request, "Confirmed food & drink reservations require a date.")
            return redirect(fallback_redirect)

    taste.title = (request.POST.get('name') or request.POST.get('title', taste.title)).strip()
    taste.taste_type = request.POST.get('category') or request.POST.get('taste_type', taste.taste_type)
    taste.status = new_status
    taste.address = request.POST.get('address', '').strip()
    taste.end_time = None
    taste.has_end_time = False
    if 'price_range' in request.POST:
        taste.price_range = request.POST.get('price_range', '').strip() or None
    if 'price' in request.POST:
        raw_price = request.POST.get('price')
        if raw_price:
            try:
                taste.price = float(raw_price)
            except (ValueError, TypeError):
                taste.price = None
        else:
            taste.price = None
    taste.currency = request.POST.get('currency', taste.currency)
    if 'menu_link' in request.POST or 'link' in request.POST:
        m_link = (request.POST.get('menu_link') or request.POST.get('link', '')).strip() or None
        taste.menu_link = m_link
        taste.link = m_link
    if 'general_link' in request.POST:
        taste.general_link = request.POST.get('general_link', '').strip() or None
    taste.description = request.POST.get('description', '').strip()
    taste.notes = request.POST.get('notes', '').strip()

    code = request.POST.get('confirmation_code', '').strip()
    if code:
        taste.confirmation_code = code

    taste.updated_by = current_user
    taste.save()
    messages.success(request, f"Updated '{taste.title}'!")
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#taste")


@require_POST
def delete_taste_view(request, trip_id, taste_id):
    trip = get_object_or_404(Trip, id=trip_id)
    taste = get_object_or_404(Taste, id=taste_id, trip=trip)
    current_user = get_current_user(request)

    if not can_user_edit_item(current_user, trip, taste):
        messages.error(request, "Permission denied: You can only delete dining spots you created or if you are a Trip Editor/Owner.")
        return redirect(f"/trips/{trip_id}/#taste")

    title = taste.title
    taste.delete()
    messages.success(request, f"'{title}' removed.")
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#taste")


# ==========================================
# Play CRUD Operations (Activities, Sights, Tours)
# ==========================================

@require_POST
def add_play_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Only Trip Owners and Editors can add activities.")
        return redirect(f"/trips/{trip_id}/#play")

    title = request.POST.get('title', '').strip()
    if not title:
        messages.error(request, "Activity title is required.")
        return redirect(f"/trips/{trip_id}/#play")

    status = _normalize_item_status(request.POST.get('status'), 'IDEA')
    play_dt, has_play_time = _parse_element_datetime(
        request,
        date_names=('date', 'play_date'),
        time_names=('time', 'play_time'),
        legacy_names=('start_time',)
    )

    if status == 'CONFIRMED' and not play_dt:
        messages.error(request, "Confirmed activities require a date.")
        return redirect(f"/trips/{trip_id}/#play")

    e_time = request.POST.get('end_time')
    end_dt = parse_datetime(e_time) if e_time else None
    if end_dt and settings.USE_TZ and timezone.is_naive(end_dt):
        end_dt = timezone.make_aware(end_dt)
    if play_dt and end_dt and end_dt < play_dt:
        messages.error(request, "End date/time cannot be before start date/time.")
        return redirect(f"/trips/{trip_id}/#play")

    play = Play(
        trip=trip,
        title=title,
        play_type=request.POST.get('play_type', 'Sightseeing'),
        status=status,
        address=request.POST.get('address', '').strip(),
        start_time=play_dt,
        end_time=None,
        has_start_time=has_play_time,
        has_end_time=False,
        price=float(request.POST.get('price')) if request.POST.get('price') else None,
        currency=request.POST.get('currency', 'USD'),
        link=request.POST.get('link', '').strip(),
        description=request.POST.get('description', '').strip(),
        notes=request.POST.get('notes', '').strip(),
        created_by=current_user,
        updated_by=current_user
    )

    code = request.POST.get('confirmation_code', '').strip()
    if code:
        play.confirmation_code = code

    play.save()
    messages.success(request, f"Activity '{play.title}' added successfully!")
    return redirect(f"/trips/{trip_id}/#play")


@require_POST
def edit_play_view(request, trip_id, play_id):
    trip = get_object_or_404(Trip, id=trip_id)
    play = get_object_or_404(Play, id=play_id, trip=trip)
    current_user = get_current_user(request)

    next_url = request.POST.get('next')
    fallback_redirect = next_url if (next_url and next_url.startswith('/')) else f"/trips/{trip_id}/#play"

    if not can_user_edit_item(current_user, trip, play):
        messages.error(request, "Permission denied: You can only edit activities you created or if you are a Trip Editor/Owner.")
        return redirect(fallback_redirect)

    new_status = _normalize_item_status(request.POST.get('status'), play.status)
    dates_in_form = any(k in request.POST for k in ('date', 'play_date', 'start_time'))

    if dates_in_form:
        play_dt, has_play_time = _parse_element_datetime(
            request,
            date_names=('date', 'play_date'),
            time_names=('time', 'play_time'),
            legacy_names=('start_time',)
        )
        if new_status == 'CONFIRMED' and not play_dt:
            messages.error(request, "Confirmed activities require a date.")
            return redirect(fallback_redirect)

        e_time = request.POST.get('end_time')
        end_dt = parse_datetime(e_time) if e_time else None
        if end_dt and settings.USE_TZ and timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)
        if play_dt and end_dt and end_dt < play_dt:
            messages.error(request, "End date/time cannot be before start date/time.")
            return redirect(fallback_redirect)

        play.start_time = play_dt
        play.has_start_time = has_play_time
    else:
        if new_status == 'CONFIRMED' and not play.start_time:
            messages.error(request, "Confirmed activities require a date.")
            return redirect(fallback_redirect)

    play.title = request.POST.get('title', play.title).strip()
    play.play_type = request.POST.get('play_type', play.play_type)
    play.status = new_status
    play.address = request.POST.get('address', '').strip()
    play.end_time = None
    play.has_end_time = False
    play.price = float(request.POST.get('price')) if request.POST.get('price') else None
    play.currency = request.POST.get('currency', play.currency)
    play.link = request.POST.get('link', '').strip()
    play.description = request.POST.get('description', '').strip()
    play.notes = request.POST.get('notes', '').strip()

    code = request.POST.get('confirmation_code', '').strip()
    if code:
        play.confirmation_code = code

    play.updated_by = current_user
    play.save()
    messages.success(request, f"Updated Activity '{play.title}'!")
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#play")


@require_POST
def delete_play_view(request, trip_id, play_id):
    trip = get_object_or_404(Trip, id=trip_id)
    play = get_object_or_404(Play, id=play_id, trip=trip)
    current_user = get_current_user(request)

    if not can_user_edit_item(current_user, trip, play):
        messages.error(request, "Permission denied: You can only delete activities you created or if you are a Trip Editor/Owner.")
        return redirect(f"/trips/{trip_id}/#play")

    title = play.title
    play.delete()
    messages.success(request, f"Activity '{title}' deleted.")
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#play")


# Backward compatibility aliases for Do & Rec
add_do_view = add_play_view
edit_do_view = edit_play_view
delete_do_view = delete_play_view
add_rec_view = add_taste_view
edit_rec_view = edit_taste_view
delete_rec_view = delete_taste_view


@require_POST
def promote_rec_view(request, trip_id, rec_id):
    """
    Promotes a recommendation from Taste or Play into a confirmed booking.
    """
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Viewers cannot promote recommendations.")
        return redirect(f"/trips/{trip_id}/#timeline")

    item = Taste.objects.filter(id=rec_id, trip=trip).first()
    target_tab = 'taste'
    if not item:
        item = Play.objects.filter(id=rec_id, trip=trip).first()
        target_tab = 'play'
    if not item:
        item = Rec.objects.filter(id=rec_id, trip=trip).first()
        target_tab = 'taste'

    if item:
        item.status = 'CONFIRMED'
        item.updated_by = current_user
        item.save()
        messages.success(request, f"'{item.title}' promoted to confirmed itinerary item!")

    return redirect(f"/trips/{trip_id}/#{target_tab}")


def public_recommend_view(request, rec_token):
    """
    Public-facing recommendation intake portal for non-trippers / friends.
    No login required. Allows anyone with the trip's unique recommendation link
    to submit recommendations that instantly populate the Taste or Play elements of the TripSpace.
    """
    trip = get_object_or_404(Trip, rec_token=rec_token)
    submitted = request.GET.get('submitted') == '1'
    current_user = get_current_user(request)

    if request.method == 'POST':
        # Honeypot spam trap
        if request.POST.get('website_url'):
            return redirect(f"{reverse('core:public_recommend', args=[rec_token])}?submitted=1")

        guest_name = request.POST.get('guest_name', '').strip()
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'Taste')
        sub_type = request.POST.get('sub_type', '').strip()
        description = request.POST.get('description', '').strip()
        address = request.POST.get('address', '').strip()
        link = request.POST.get('link', '').strip()

        if not guest_name or not title:
            messages.error(request, "Please provide your name and the place or activity title.")
            return render(request, 'public_recommend.html', {
                'trip': trip,
                'submitted': False,
                'form_data': request.POST,
                'current_user': current_user,
                'existing_tastes': trip.tastes.order_by('-created_at')[:6],
                'existing_plays': trip.plays.order_by('-created_at')[:6],
            })

        if category == 'Taste' or category in ('Food', 'Dining'):
            taste_type = sub_type if sub_type else 'Restaurant'
            Taste.objects.create(
                trip=trip,
                title=title,
                taste_type=taste_type,
                status='IDEA',
                description=description,
                address=address,
                link=link,
                guest_name=guest_name,
                recommended_by=current_user if current_user else None,
                updated_by=current_user if current_user else None,
            )
        else:
            play_type = sub_type if sub_type else 'Sightseeing'
            Play.objects.create(
                trip=trip,
                title=title,
                play_type=play_type,
                status='IDEA',
                description=description,
                address=address,
                link=link,
                guest_name=guest_name,
                recommended_by=current_user if current_user else None,
                updated_by=current_user if current_user else None,
            )

        return redirect(f"{reverse('core:public_recommend', args=[rec_token])}?submitted=1")

    existing_tastes = trip.tastes.order_by('-created_at')[:6]
    existing_plays = trip.plays.order_by('-created_at')[:6]
    return render(request, 'public_recommend.html', {
        'trip': trip,
        'submitted': submitted,
        'current_user': current_user,
        'existing_tastes': existing_tastes,
        'existing_plays': existing_plays,
    })


# ==========================================
# Vault & Attachments Operations
# ==========================================

ALLOWED_VAULT_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}


def sanitize_display_filename(raw_name: str) -> str:
    """Strips directory components and control characters from a display filename."""
    base = os.path.basename(raw_name or 'Document').strip()
    cleaned = ''.join(ch for ch in base if ch.isprintable() and ch not in {'/', '\\', '\x00'})
    return (cleaned or 'Document')[:255]


def validate_and_sanitize_vault_file(file_obj):
    """
    Validates uploaded Vault files using size limits, extension allowlists, and
    cryptographic magic-byte header inspection to block polyglot/XSS uploads.
    Returns (is_valid, error_message, detected_mime, safe_ext).
    """
    max_mb = getattr(settings, 'MAX_VAULT_UPLOAD_SIZE_MB', 10)
    max_bytes = max_mb * 1024 * 1024
    if file_obj.size > max_bytes:
        return False, f"File exceeds the maximum allowed size of {max_mb} MB.", None, None

    _, ext = os.path.splitext((file_obj.name or '').lower())
    if ext not in ALLOWED_VAULT_EXTENSIONS:
        return False, "Unsupported file extension. Only PDF, PNG, and JPEG documents are allowed in the Vault.", None, None

    header = file_obj.read(16)
    file_obj.seek(0)

    if header.startswith(b'%PDF-'):
        detected_mime, safe_ext = 'application/pdf', '.pdf'
    elif header.startswith(b'\x89PNG\r\n\x1a\n'):
        detected_mime, safe_ext = 'image/png', '.png'
    elif header.startswith(b'\xff\xd8\xff'):
        detected_mime, safe_ext = 'image/jpeg', '.jpg' if ext == '.jpg' else '.jpeg'
    else:
        return False, "File signature verification failed: file content does not match a valid PDF, PNG, or JPEG.", None, None

    # Ensure extension aligns with detected magic bytes
    if (detected_mime == 'application/pdf' and ext != '.pdf') or \
       (detected_mime == 'image/png' and ext != '.png') or \
       (detected_mime == 'image/jpeg' and ext not in {'.jpg', '.jpeg'}):
        return False, "File extension does not match its actual binary content.", None, None

    return True, None, detected_mime, safe_ext


@require_POST
def upload_attachment_view(request, trip_id):
    """Uploads a booking document, ticket, or receipt to the Vault."""
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Viewers cannot upload vault documents.")
        return redirect(f"/trips/{trip_id}/#vault")

    file_obj = request.FILES.get('file')
    raw_file_name = request.POST.get('file_name') or (file_obj.name if file_obj else 'Document')
    file_name = sanitize_display_filename(raw_file_name)
    detected_mime = 'application/pdf'

    if file_obj:
        is_valid, err_msg, detected_mime, safe_ext = validate_and_sanitize_vault_file(file_obj)
        if not is_valid:
            messages.error(request, err_msg)
            return redirect(f"/trips/{trip_id}/#vault")
        # Randomize storage filename to prevent path traversal and enumeration
        randomized_name = f"{uuid.uuid4().hex}{safe_ext}"
        file_obj.name = randomized_name
        storage_path = f"vault/{trip.id}/{randomized_name}"
    else:
        storage_path = f"vault/{trip.id}/{uuid.uuid4().hex}.pdf"

    stay_id = request.POST.get('stay_id')
    move_id = request.POST.get('move_id') or request.POST.get('nav_id')
    taste_id = request.POST.get('taste_id')
    play_id = request.POST.get('play_id') or request.POST.get('do_id')

    attachment = Attachment(
        trip=trip,
        file_name=file_name,
        file_type=detected_mime,
        file=file_obj,
        storage_path=storage_path,
        uploaded_by=current_user,
        updated_by=current_user
    )

    if stay_id:
        attachment.stay = Stay.objects.filter(id=stay_id, trip=trip).first()
    if move_id:
        attachment.move = Move.objects.filter(id=move_id, trip=trip).first()
        attachment.nav = Nav.objects.filter(id=move_id, trip=trip).first()
    if taste_id:
        attachment.taste = Taste.objects.filter(id=taste_id, trip=trip).first()
    if play_id:
        attachment.play = Play.objects.filter(id=play_id, trip=trip).first()
        attachment.do = Do.objects.filter(id=play_id, trip=trip).first()

    attachment.save()
    log_security_event(
        request,
        action='VAULT_DOCUMENT_UPLOADED',
        resource_type='ATTACHMENT',
        resource_id=attachment.id,
        trip=trip,
        user=current_user,
        metadata={'file_name': attachment.file_name, 'file_type': attachment.file_type}
    )
    messages.success(request, f"Uploaded '{attachment.file_name}' to the Vault!")
    return redirect(f"/trips/{trip_id}/#vault")


@require_GET
def download_attachment_view(request, trip_id, attachment_id):
    """
    Authenticated, RBAC-checked, and time-limited cryptographically signed
    endpoint for downloading Vault documents.
    """
    trip = get_object_or_404(Trip, id=trip_id)
    attachment = get_object_or_404(Attachment, id=attachment_id, trip=trip)
    current_user = get_current_user(request)

    if not current_user:
        return HttpResponseForbidden("Authentication required.")

    role = get_user_trip_role(current_user, trip)
    if not role:
        return HttpResponseForbidden("Access denied: You are not a member of this trip.")

    token = request.GET.get('token', '')
    if not token:
        return HttpResponseForbidden("Missing signed download token.")

    signer = TimestampSigner(salt='sonderring.vault.download')
    max_age = getattr(settings, 'VAULT_SIGNED_URL_EXPIRY_SECONDS', 900)
    try:
        unsigned_val = signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return HttpResponseForbidden("Invalid or expired download link.")

    expected_val = f"{trip.id}:{attachment.id}"
    if unsigned_val != expected_val:
        return HttpResponseForbidden("Token scope mismatch.")

    if not attachment.file:
        return HttpResponseBadRequest("No physical file attached to this Vault record.")

    log_security_event(
        request,
        action='VAULT_DOCUMENT_ACCESSED',
        resource_type='ATTACHMENT',
        resource_id=attachment.id,
        trip=trip,
        user=current_user,
        metadata={'file_name': attachment.file_name, 'role': role}
    )

    response = FileResponse(
        attachment.file.open('rb'),
        as_attachment=True,
        filename=sanitize_display_filename(attachment.file_name),
        content_type=attachment.file_type or 'application/octet-stream',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@require_POST
def delete_attachment_view(request, trip_id, attachment_id):
    trip = get_object_or_404(Trip, id=trip_id)
    attachment = get_object_or_404(Attachment, id=attachment_id, trip=trip)
    current_user = get_current_user(request)

    if not can_user_edit_item(current_user, trip, attachment):
        messages.error(request, "Permission denied: You can only delete documents you uploaded or if you are a Trip Editor/Owner.")
        return redirect(f"/trips/{trip_id}/#vault")

    file_name = attachment.file_name
    att_id = attachment.id
    attachment.delete()
    log_security_event(
        request,
        action='VAULT_DOCUMENT_DELETED',
        resource_type='ATTACHMENT',
        resource_id=att_id,
        trip=trip,
        user=current_user,
        metadata={'file_name': file_name}
    )
    messages.success(request, f"Document '{file_name}' removed from Vault.")
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"/trips/{trip_id}/#vault")


# ==========================================
# Tripper & Member Management Operations
# ==========================================

@require_POST
def invite_member_view(request, trip_id):
    """Invites a companion / tripper to the trip with an assigned role."""
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not can_user_edit_trip(current_user, trip):
        messages.error(request, "Permission denied: Viewers cannot invite companions.")
        return redirect(f"/trips/{trip_id}/")

    user_id = request.POST.get('user_id', '').strip()
    handle_or_email = request.POST.get('handle_or_email', '').strip()
    role = request.POST.get('role', 'EDITOR').strip().upper()
    if role not in ('EDITOR', 'VIEWER'):
        role = 'EDITOR'

    user = None
    if handle_or_email:
        clean_handle = handle_or_email.lstrip('@')
        user = UserProfile.objects.filter(
            Q(handle__iexact=clean_handle) | Q(email__iexact=handle_or_email),
            is_active=True
        ).first()
        if not user:
            messages.error(request, f"No active traveler found matching '{handle_or_email}'.")
            return redirect(f"/trips/{trip_id}/")
    elif user_id:
        user = get_object_or_404(UserProfile, id=user_id, is_active=True)
    else:
        messages.error(request, "Please specify a handle, email, or user to invite.")
        return redirect(f"/trips/{trip_id}/")

    membership, created = TripMember.objects.get_or_create(
        trip=trip,
        user=user,
        defaults={'role': role}
    )
    if not created:
        membership.role = role
        membership.save()

    log_security_event(
        request,
        action='MEMBER_INVITED' if created else 'MEMBER_ROLE_CHANGED',
        resource_type='MEMBER',
        resource_id=membership.id,
        trip=trip,
        user=current_user,
        metadata={'target_user_handle': user.handle, 'role': role}
    )
    messages.success(request, f"Added @{user.handle} as {role} to {trip.title}!")
    return redirect(f"/trips/{trip_id}/")


@require_POST
def update_member_role_view(request, trip_id, member_id):
    """Updates a tripper's role. Restricted to Trip Owner."""
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not is_user_trip_owner(current_user, trip):
        messages.error(request, "Permission denied: Only the Trip Owner can modify member permissions.")
        return redirect(f"/trips/{trip_id}/")

    member = get_object_or_404(TripMember, id=member_id, trip=trip)
    old_role = member.role
    new_role = request.POST.get('role', 'EDITOR').strip().upper()
    if new_role not in ('OWNER', 'EDITOR', 'VIEWER'):
        new_role = 'EDITOR'
    member.role = new_role
    member.save()

    log_security_event(
        request,
        action='MEMBER_ROLE_CHANGED',
        resource_type='MEMBER',
        resource_id=member.id,
        trip=trip,
        user=current_user,
        metadata={'target_user_handle': member.user.handle, 'old_role': old_role, 'new_role': new_role}
    )
    messages.success(request, f"Updated @{member.user.handle}'s role to {new_role}.")
    return redirect(f"/trips/{trip_id}/")


@require_POST
def remove_member_view(request, trip_id, member_id):
    """Removes a tripper from the trip. Restricted to Trip Owner."""
    trip = get_object_or_404(Trip, id=trip_id)
    current_user = get_current_user(request)

    if not is_user_trip_owner(current_user, trip):
        messages.error(request, "Permission denied: Only the Trip Owner can remove companions.")
        return redirect(f"/trips/{trip_id}/")

    member = get_object_or_404(TripMember, id=member_id, trip=trip)
    handle = member.user.handle
    mem_id = member.id
    member.delete()

    log_security_event(
        request,
        action='MEMBER_REMOVED',
        resource_type='MEMBER',
        resource_id=mem_id,
        trip=trip,
        user=current_user,
        metadata={'removed_user_handle': handle}
    )
    messages.success(request, f"Removed @{handle} from this trip.")
    return redirect(f"/trips/{trip_id}/")


# ==========================================
# Interactive AJAX Endpoints
# ==========================================

@require_POST
def toggle_item_status_view(request, item_type, item_id):
    """Cycles or updates trip element status (Idea -> Confirmed -> Complete -> Idea) via AJAX."""
    current_user = get_current_user(request)
    model_map = {
        'move': Move,
        'stay': Stay,
        'taste': Taste,
        'play': Play,
        'nav': Nav,
        'do': Do,
        'rec': Rec,
    }
    model = model_map.get(item_type.lower())
    if not model:
        return HttpResponseBadRequest("Invalid item type.")

    item = get_object_or_404(model, id=item_id)
    if not can_user_edit_item(current_user, item.trip, item):
        return HttpResponseForbidden("You can only modify status of items you created or if you are a Trip Editor/Owner.")

    explicit_status = request.POST.get('status', '').strip().upper()
    if explicit_status in ('IDEA', 'CONFIRMED', 'COMPLETE'):
        item.status = explicit_status
    else:
        cycle_map = {
            'IDEA': 'CONFIRMED',
            'CONFIRMED': 'COMPLETE',
            'COMPLETE': 'IDEA',
        }
        item.status = cycle_map.get(item.status, 'IDEA')

    item.updated_by = current_user
    item.save()

    return JsonResponse({
        'success': True,
        'item_id': str(item.id),
        'new_status': item.status,
        'status_display': item.get_status_display(),
        'confirmed_count': item.trip.confirmed_items_count,
        'idea_count': item.trip.idea_items_count,
        'complete_count': item.trip.complete_items_count,
    })


@require_GET
def reveal_confirmation_code_view(request, item_type, item_id):
    """Secure on-demand decryption endpoint strictly scoped to authorized trippers."""
    current_user = get_current_user(request)
    if not current_user:
        return JsonResponse(
            {'success': False, 'error': 'Authentication required to reveal confirmation codes.'},
            status=403
        )

    model_map = {
        'move': Move,
        'stay': Stay,
        'taste': Taste,
        'play': Play,
        'nav': Nav,
        'do': Do,
    }
    model = model_map.get(item_type.lower())
    if not model:
        return HttpResponseBadRequest("Invalid item type.")

    item = get_object_or_404(model, id=item_id)
    if not get_user_trip_role(current_user, item.trip):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied: You are not an authorized member of this trip.'},
            status=403
        )

    rate_key = f"ratelimit:reveal:{current_user.id}"
    max_reveals = getattr(settings, 'REVEAL_CODE_RATE_LIMIT_PER_MIN', 15)
    if is_rate_limited(rate_key, max_reveals):
        return JsonResponse(
            {'success': False, 'error': 'Rate limit exceeded. Please wait before revealing more codes.'},
            status=429
        )
    increment_rate_limit(rate_key, 60)

    code = item.confirmation_code

    if not code:
        return JsonResponse({'success': False, 'error': 'No confirmation code set on this item.'})

    log_security_event(
        request,
        action='CONFIRMATION_CODE_REVEALED',
        resource_type=item_type.upper(),
        resource_id=item.id,
        trip=item.trip,
        user=current_user,
        metadata={'item_title': item.title}
    )

    return JsonResponse({
        'success': True,
        'item_id': str(item.id),
        'code': code
    })
