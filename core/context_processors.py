from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from core.models import UserProfile, Trip, order_current_and_upcoming_trips


def auth_feature_flags(request):
    """
    Exposes authentication/OAuth feature flags and global navbar context
    (active TripSpaces dropdown items & current year for the global Create Trip modal).
    """
    nav_active_trips = Trip.objects.none()
    user_id = request.session.get('user_id')
    if user_id:
        user = UserProfile.objects.filter(id=user_id, is_active=True).first()
        if user:
            user_trips = Trip.objects.filter(
                Q(created_by=user) | Q(members__user=user)
            ).distinct()
            nav_active_trips = order_current_and_upcoming_trips(user_trips)

    return {
        'ENABLE_GOOGLE_OAUTH': getattr(settings, 'ENABLE_GOOGLE_OAUTH', False),
        'ENABLE_DEMO_SWITCHER': getattr(settings, 'ENABLE_DEMO_SWITCHER', False),
        'nav_active_trips': nav_active_trips,
        'now_year': timezone.now().year,
    }
