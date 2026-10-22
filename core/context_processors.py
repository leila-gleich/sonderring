from django.conf import settings

def auth_feature_flags(request):
    """
    Exposes authentication and OAuth feature flags to all templates.
    """
    return {
        'ENABLE_GOOGLE_OAUTH': getattr(settings, 'ENABLE_GOOGLE_OAUTH', False),
    }
