from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.template.context import BaseContext
from core.models import UserProfile, OAuthIdentity, Trip, TripMember, Stay, Nav, Do, Rec

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


class TripAuthorizationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_a = UserProfile.objects.create(
            email='user_a@example.com',
            handle='usera',
            full_name='User A',
            is_active=True
        )
        self.user_b = UserProfile.objects.create(
            email='user_b@example.com',
            handle='userb',
            full_name='User B',
            is_active=True
        )
        self.trip_a = Trip.objects.create(
            title='Secret Trip A',
            location='Malta',
            year=2026,
            time_granularity='YEAR',
            created_by=self.user_a
        )
        TripMember.objects.create(trip=self.trip_a, user=self.user_a, role='OWNER')

    def test_dashboard_does_not_leak_unrelated_trips(self):
        """User B should not see User A's trips on the dashboard."""
        session = self.client.session
        session['user_id'] = str(self.user_b.id)
        session.save()

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Secret Trip A')

    def test_dashboard_shows_invited_trip(self):
        """User B should see User A's trip once added as a collaborator."""
        TripMember.objects.create(trip=self.trip_a, user=self.user_b, role='EDITOR')

        session = self.client.session
        session['user_id'] = str(self.user_b.id)
        session.save()

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Secret Trip A')

    def test_unauthorized_user_blocked_from_workspace(self):
        """User B cannot access trip_a workspace if not invited."""
        session = self.client.session
        session['user_id'] = str(self.user_b.id)
        session.save()

        response = self.client.get(reverse('core:trip_workspace', args=[self.trip_a.id]))
        self.assertRedirects(response, reverse('core:dashboard'))

    def tearDown(self):
        from core.md_sync import delete_trip_markdown
        for t in Trip.objects.all():
            delete_trip_markdown(t)


class TripStatusTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = UserProfile.objects.create(
            email='owner@example.com',
            handle='tripowner',
            full_name='Trip Owner',
            is_active=True
        )
        self.viewer = UserProfile.objects.create(
            email='viewer@example.com',
            handle='tripviewer',
            full_name='Trip Viewer',
            is_active=True
        )
        self.trip = Trip.objects.create(
            title='Status Lifecycle Trip',
            location='Sicily',
            status='IDEA',
            year=2026,
            time_granularity='YEAR',
            created_by=self.owner
        )
        TripMember.objects.create(trip=self.trip, user=self.owner, role='OWNER')
        TripMember.objects.create(trip=self.trip, user=self.viewer, role='VIEWER')

    def tearDown(self):
        from core.md_sync import delete_trip_markdown
        for t in Trip.objects.all():
            delete_trip_markdown(t)

    def test_trip_status_transitions_idea_confirmed_complete(self):
        """Verify owner can transition trip between IDEA, CONFIRMED, and COMPLETE."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        # Initially IDEA
        self.assertEqual(self.trip.status, 'IDEA')

        # Transition to CONFIRMED
        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'CONFIRMED'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'CONFIRMED')

        # Transition to COMPLETE
        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'COMPLETE'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'COMPLETE')

        # Transition back to IDEA (Tentative)
        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'IDEA'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'IDEA')

    def test_viewer_cannot_change_trip_status(self):
        """Verify viewers cannot change trip status."""
        session = self.client.session
        session['user_id'] = str(self.viewer.id)
        session.save()

        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'COMPLETE'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'IDEA')


class AccessControlAndRBACTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = UserProfile.objects.create(
            email='owner_rbac@example.com',
            handle='ownerrbac',
            full_name='Owner RBAC',
            is_active=True
        )
        self.viewer = UserProfile.objects.create(
            email='viewer_rbac@example.com',
            handle='viewerrbac',
            full_name='Viewer RBAC',
            is_active=True
        )
        self.outsider = UserProfile.objects.create(
            email='outsider@example.com',
            handle='outsider',
            full_name='Outsider User',
            is_active=True
        )
        self.trip = Trip.objects.create(
            title='RBAC Secured Trip',
            location='Reykjavik',
            year=2026,
            time_granularity='YEAR',
            created_by=self.owner
        )
        TripMember.objects.create(trip=self.trip, user=self.owner, role='OWNER')
        TripMember.objects.create(trip=self.trip, user=self.viewer, role='VIEWER')

        self.stay = Stay(
            trip=self.trip,
            title='Grand Hotel',
            status='CONFIRMED',
            created_by=self.owner
        )
        self.stay.confirmation_code = 'SECRET-PNR-999'
        self.stay.save()

    def tearDown(self):
        from core.md_sync import delete_trip_markdown
        for t in Trip.objects.all():
            delete_trip_markdown(t)

    def test_reveal_code_blocks_unauthenticated_and_outsiders(self):
        """Unauthenticated requests and non-members must receive 403 Forbidden on reveal-code."""
        url = reverse('core:reveal_code', args=['stay', self.stay.id])

        # 1. Unauthenticated
        resp_unauth = self.client.get(url)
        self.assertEqual(resp_unauth.status_code, 403)
        self.assertNotIn('SECRET-PNR-999', resp_unauth.content.decode())

        # 2. Authenticated outsider (not on trip)
        session = self.client.session
        session['user_id'] = str(self.outsider.id)
        session.save()
        resp_outsider = self.client.get(url)
        self.assertEqual(resp_outsider.status_code, 403)
        self.assertNotIn('SECRET-PNR-999', resp_outsider.content.decode())

        # 3. Authorized member (Viewer) can reveal
        session['user_id'] = str(self.viewer.id)
        session.save()
        resp_member = self.client.get(url)
        self.assertEqual(resp_member.status_code, 200)
        self.assertEqual(resp_member.json().get('code'), 'SECRET-PNR-999')

    def test_viewer_cannot_add_stays_navs_dos_or_recs(self):
        """Viewers must be blocked from creating Stays, Navs, Dos, or Recs."""
        session = self.client.session
        session['user_id'] = str(self.viewer.id)
        session.save()

        self.client.post(reverse('core:add_stay', args=[self.trip.id]), {'title': 'Unauthorized Stay'})
        self.assertFalse(Stay.objects.filter(trip=self.trip, title='Unauthorized Stay').exists())

        self.client.post(reverse('core:add_nav', args=[self.trip.id]), {'title': 'Unauthorized Nav', 'mode': 'Flight'})
        self.assertFalse(Nav.objects.filter(trip=self.trip, title='Unauthorized Nav').exists())

        self.client.post(reverse('core:add_do', args=[self.trip.id]), {'title': 'Unauthorized Do'})
        self.assertFalse(Do.objects.filter(trip=self.trip, title='Unauthorized Do').exists())

        self.client.post(reverse('core:add_rec', args=[self.trip.id]), {'title': 'Unauthorized Rec'})
        self.assertFalse(Rec.objects.filter(trip=self.trip, title='Unauthorized Rec').exists())

    @override_settings(ENABLE_DEMO_SWITCHER=False)
    def test_demo_switcher_disabled_blocks_impersonation(self):
        """When ENABLE_DEMO_SWITCHER is False, switch-user and demo_user_id login return 403."""
        resp_switch = self.client.post(reverse('core:switch_user'), {'user_id': str(self.owner.id)})
        self.assertEqual(resp_switch.status_code, 403)
        self.assertIsNone(self.client.session.get('user_id'))

        resp_demo_login = self.client.post(reverse('core:login'), {'demo_user_id': str(self.owner.id)})
        self.assertEqual(resp_demo_login.status_code, 403)
        self.assertIsNone(self.client.session.get('user_id'))



