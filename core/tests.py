from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.template.context import BaseContext
from core.models import UserProfile, OAuthIdentity

# Patch BaseContext.__copy__ for Python 3.14 compatibility with Django 4.2 test runner
def _patched_copy(self):
    dup = self.__class__.__new__(self.__class__)
    dup.__dict__.update(self.__dict__)
    dup.dicts = self.dicts[:]
    return dup

BaseContext.__copy__ = _patched_copy



class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.create(
            email='testuser@example.com',
            handle='testuser',
            full_name='Test User',
            is_active=True
        )
        self.user.set_password('SecretPass123!')
        self.user.save()

    def test_user_password_hashing(self):
        """Verify PBKDF2 password hashing and verification methods."""
        self.assertTrue(self.user.check_password('SecretPass123!'))
        self.assertFalse(self.user.check_password('WrongPass!'))
        self.assertTrue(self.user.has_usable_password())

    def test_signup_success(self):
        """Verify new user registration creates UserProfile with hashed password."""
        response = self.client.post(reverse('core:signup'), {
            'full_name': 'New Traveler',
            'handle': 'newtraveler',
            'email': 'newtraveler@example.com',
            'password': 'SecurePassword2026!',
            'password_confirm': 'SecurePassword2026!',
        })
        self.assertRedirects(response, reverse('core:dashboard'))
        created = UserProfile.objects.filter(handle='newtraveler').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.full_name, 'New Traveler')
        self.assertTrue(created.check_password('SecurePassword2026!'))
        self.assertEqual(self.client.session.get('user_id'), str(created.id))

    def test_signup_validation_mismatched_password(self):
        """Verify signup fails when passwords do not match."""
        response = self.client.post(reverse('core:signup'), {
            'full_name': 'New Traveler',
            'handle': 'newtraveler2',
            'email': 'newtraveler2@example.com',
            'password': 'SecurePassword2026!',
            'password_confirm': 'DifferentPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserProfile.objects.filter(handle='newtraveler2').exists())

    def test_login_with_email_success(self):
        """Verify login with email and correct password."""
        response = self.client.post(reverse('core:login'), {
            'handle_or_email': 'testuser@example.com',
            'password': 'SecretPass123!',
        })
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(self.client.session.get('user_id'), str(self.user.id))

    def test_login_with_handle_success(self):
        """Verify login with @handle and correct password."""
        response = self.client.post(reverse('core:login'), {
            'handle_or_email': '@testuser',
            'password': 'SecretPass123!',
        })
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(self.client.session.get('user_id'), str(self.user.id))

    def test_login_invalid_password(self):
        """Verify login fails with wrong password."""
        response = self.client.post(reverse('core:login'), {
            'handle_or_email': 'testuser@example.com',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get('user_id'))

    def test_logout(self):
        """Verify logout clears the session."""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()

        response = self.client.get(reverse('core:logout'))
        self.assertRedirects(response, reverse('core:login'))
        self.assertIsNone(self.client.session.get('user_id'))

    def test_change_password(self):
        """Verify changing password updates hash."""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()

        response = self.client.post(reverse('core:change_password'), {
            'old_password': 'SecretPass123!',
            'new_password': 'BrandNewPass999!',
            'new_password_confirm': 'BrandNewPass999!',
        })
        self.assertRedirects(response, reverse('core:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPass999!'))
        self.assertFalse(self.user.check_password('SecretPass123!'))

    def test_protected_dashboard_redirects_unauthenticated(self):
        """Verify accessing dashboard without login redirects to login."""
        response = self.client.get(reverse('core:dashboard'))
        self.assertRedirects(response, f"{reverse('core:login')}?next=/")


class OAuthFeatureFlagTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.create(
            email='oauthuser@example.com',
            handle='oauthuser',
            full_name='OAuth User'
        )
        self.user.set_password('Pass123456!')
        self.user.save()

    @override_settings(ENABLE_GOOGLE_OAUTH=False)
    def test_oauth_disabled_returns_404_and_hides_button(self):
        """When ENABLE_GOOGLE_OAUTH is False, button is hidden and endpoint returns 404."""
        # 1. Login page does not render Google sign-in button
        response = self.client.get(reverse('core:login'))
        self.assertNotContains(response, 'Continue with Google')

        # 2. OAuth login endpoint returns 404
        oauth_response = self.client.get(reverse('oauth:google_login'))
        self.assertEqual(oauth_response.status_code, 404)

    @override_settings(
        ENABLE_GOOGLE_OAUTH=True,
        GOOGLE_CLIENT_ID='test-client-id.apps.googleusercontent.com',
        GOOGLE_CLIENT_SECRET='test-secret'
    )
    def test_oauth_enabled_renders_button_and_redirects(self):
        """When ENABLE_GOOGLE_OAUTH is True and configured, renders button and redirects."""
        # 1. Login page renders Google sign-in button
        response = self.client.get(reverse('core:login'))
        self.assertContains(response, 'Continue with Google')

        # 2. OAuth login endpoint redirects to Google accounts URL
        oauth_response = self.client.get(reverse('oauth:google_login'))
        self.assertEqual(oauth_response.status_code, 302)
        self.assertTrue(oauth_response.url.startswith('https://accounts.google.com/o/oauth2/v2/auth'))
        self.assertIn('client_id=test-client-id.apps.googleusercontent.com', oauth_response.url)
        self.assertIn('state=', oauth_response.url)

    def test_oauth_unlink_safeguard(self):
        """User cannot unlink Google if no password is set."""
        user_no_pass = UserProfile.objects.create(
            email='nopass@example.com',
            handle='nopass',
            full_name='No Pass User'
        )
        OAuthIdentity.objects.create(
            user=user_no_pass,
            provider='google',
            uid='sub-12345',
            email='nopass@example.com'
        )
        session = self.client.session
        session['user_id'] = str(user_no_pass.id)
        session.save()

        response = self.client.post(reverse('oauth:google_unlink'))
        self.assertRedirects(response, reverse('core:profile'))
        # Identity still exists because unlink was blocked
        self.assertTrue(OAuthIdentity.objects.filter(user=user_no_pass, provider='google').exists())
