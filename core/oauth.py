import json
import secrets
import urllib.parse
import urllib.request
from django.conf import settings
from django.utils import timezone
from .models import UserProfile, OAuthIdentity


def is_google_oauth_enabled():
    """Returns True if Google OAuth is enabled in settings."""
    return getattr(settings, 'ENABLE_GOOGLE_OAUTH', False)


def is_google_oauth_configured():
    """Returns True if Google OAuth is enabled AND client credentials exist."""
    return (
        is_google_oauth_enabled()
        and bool(getattr(settings, 'GOOGLE_CLIENT_ID', ''))
        and bool(getattr(settings, 'GOOGLE_CLIENT_SECRET', ''))
    )


def get_google_auth_url(request):
    """
    Constructs the Google OAuth 2.0 / OpenID Connect authorization URL.
    Saves a cryptographically secure state token in session to prevent CSRF.
    """
    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state

    redirect_uri = getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', '')
    if not redirect_uri:
        redirect_uri = request.build_absolute_uri('/oauth/google/callback/')

    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_code_for_userinfo(code, redirect_uri):
    """
    Exchanges authorization code for Google userinfo profile.
    Uses standard library urllib without adding external dependencies.
    """
    token_url = 'https://oauth2.googleapis.com/token'
    payload = urllib.parse.urlencode({
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }).encode('utf-8')

    token_req = urllib.request.Request(
        token_url,
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )

    with urllib.request.urlopen(token_req, timeout=10) as response:
        token_data = json.loads(response.read().decode('utf-8'))

    access_token = token_data.get('access_token')
    if not access_token:
        raise ValueError("Google OAuth token response did not contain an access_token")

    # Fetch userinfo
    userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    userinfo_req = urllib.request.Request(
        userinfo_url,
        headers={'Authorization': f"Bearer {access_token}"}
    )

    with urllib.request.urlopen(userinfo_req, timeout=10) as response:
        claims = json.loads(response.read().decode('utf-8'))

    return claims


def authenticate_or_link_google_user(claims, current_user=None):
    """
    Resolves a verified Google user claims dictionary to a UserProfile.
    
    1. If current_user is passed, links Google identity to this active profile.
    2. If OAuthIdentity exists with (google, sub), returns that user.
    3. If UserProfile exists with the same email, attaches OAuthIdentity and returns user.
    4. Otherwise, creates a new UserProfile + OAuthIdentity and returns user.
    """
    sub = claims.get('sub')
    email = claims.get('email', '').strip().lower()
    name = claims.get('name') or claims.get('given_name') or email.split('@')[0].title()
    picture = claims.get('picture')

    if not sub or not email:
        raise ValueError("Incomplete Google claims: missing 'sub' or 'email'")

    # Case 1: Linking an existing logged-in session to Google
    if current_user:
        identity, created = OAuthIdentity.objects.get_or_create(
            user=current_user,
            provider='google',
            defaults={'uid': sub, 'email': email, 'extra_data': claims}
        )
        if not created and identity.uid != sub:
            identity.uid = sub
            identity.email = email
            identity.extra_data = claims
            identity.save()
        return current_user, 'linked'

    # Case 2: Matching by existing OAuth identity
    existing_identity = OAuthIdentity.objects.filter(provider='google', uid=sub).select_related('user').first()
    if existing_identity:
        user = existing_identity.user
        user.last_login = timezone.now()
        if picture and not user.profile_image_url:
            user.profile_image_url = picture
        user.save(update_fields=['last_login', 'profile_image_url'])
        return user, 'logged_in'

    # Case 3: Matching by verified email to an existing UserProfile
    user = UserProfile.objects.filter(email__iexact=email).first()
    if user:
        OAuthIdentity.objects.create(
            user=user,
            provider='google',
            uid=sub,
            email=email,
            extra_data=claims
        )
        user.last_login = timezone.now()
        if picture and not user.profile_image_url:
            user.profile_image_url = picture
        user.save(update_fields=['last_login', 'profile_image_url'])
        return user, 'linked_and_logged_in'

    # Case 4: Creating a brand new UserProfile
    base_handle = email.split('@')[0].lower()
    # Sanitize handle: alphanumeric and underscores only
    clean_handle = ''.join(c for c in base_handle if c.isalnum() or c == '_')[:30] or 'traveler'
    candidate_handle = clean_handle
    counter = 1
    while UserProfile.objects.filter(handle__iexact=candidate_handle).exists():
        candidate_handle = f"{clean_handle[:25]}{counter}"
        counter += 1

    new_user = UserProfile.objects.create(
        email=email,
        handle=candidate_handle,
        full_name=name,
        profile_image_url=picture or '',
        last_login=timezone.now(),
        is_active=True
    )

    OAuthIdentity.objects.create(
        user=new_user,
        provider='google',
        uid=sub,
        email=email,
        extra_data=claims
    )

    return new_user, 'created'
