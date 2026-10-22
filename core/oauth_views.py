from django.shortcuts import redirect
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.contrib import messages
from django.conf import settings
from .oauth import (
    is_google_oauth_enabled,
    is_google_oauth_configured,
    get_google_auth_url,
    exchange_code_for_userinfo,
    authenticate_or_link_google_user,
)
from .models import UserProfile, OAuthIdentity


def get_current_user_or_none(request):
    user_id = request.session.get('user_id')
    if user_id:
        return UserProfile.objects.filter(id=user_id, is_active=True).first()
    return None


def google_login_view(request):
    """
    Redirects user to Google OAuth consent page.
    Safe: if OAuth is disabled, safely redirects to login with info message.
    """
    if not is_google_oauth_enabled():
        return HttpResponseNotFound("OAuth is currently disabled.")

    if not is_google_oauth_configured():
        messages.warning(
            request,
            "Google OAuth is currently in internal exploration mode. "
            "Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in settings or environment."
        )
        return redirect('core:login')

    auth_url = get_google_auth_url(request)
    return redirect(auth_url)


def google_callback_view(request):
    """
    Handles Google OAuth redirect back to Sonderring.
    Verifies state token (anti-CSRF) and resolves or links user account.
    """
    if not is_google_oauth_enabled():
        return HttpResponseNotFound("OAuth is currently disabled.")

    # Check for errors returned from Google
    error = request.GET.get('error')
    if error:
        messages.error(request, f"Google sign-in was cancelled or failed ({error}).")
        return redirect('core:login')

    # Verify CSRF state parameter
    expected_state = request.session.pop('google_oauth_state', None)
    received_state = request.GET.get('state')
    if not expected_state or expected_state != received_state:
        return HttpResponseBadRequest("Invalid OAuth state token. Possible CSRF attempt.")

    code = request.GET.get('code')
    if not code:
        return HttpResponseBadRequest("Missing authorization code from Google.")

    redirect_uri = getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', '')
    if not redirect_uri:
        redirect_uri = request.build_absolute_uri('/oauth/google/callback/')

    try:
        claims = exchange_code_for_userinfo(code, redirect_uri)
    except Exception as e:
        messages.error(request, f"Failed to exchange token with Google: {str(e)}")
        return redirect('core:login')

    current_user = get_current_user_or_none(request)
    try:
        user, action = authenticate_or_link_google_user(claims, current_user=current_user)
        request.session['user_id'] = str(user.id)

        if action == 'linked':
            messages.success(request, f"Successfully linked your Google account ({claims.get('email')})!")
            return redirect('core:profile')
        elif action == 'created':
            messages.success(request, f"Welcome to Sonderring, {user.full_name}! Your Google account has been connected.")
        else:
            messages.success(request, f"Welcome back, {user.full_name}!")

        return redirect('core:dashboard')
    except Exception as e:
        messages.error(request, f"Error processing user profile: {str(e)}")
        return redirect('core:login')


def unlink_google_view(request):
    """
    Allows a user to unlink their Google account from their profile.
    Ensures the user has an active password set so they don't get locked out.
    """
    current_user = get_current_user_or_none(request)
    if not current_user:
        return redirect('core:login')

    if not current_user.has_usable_password():
        messages.error(
            request,
            "You must set a password for your Sonderring account before unlinking your Google login, "
            "otherwise you will not be able to log in."
        )
        return redirect('core:profile')

    deleted_count, _ = OAuthIdentity.objects.filter(user=current_user, provider='google').delete()
    if deleted_count > 0:
        messages.success(request, "Google login unlinked. You can now log in using your email and password.")
    else:
        messages.info(request, "No linked Google account was found.")

    return redirect('core:profile')
