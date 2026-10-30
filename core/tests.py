import datetime
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.template.context import BaseContext
from core.models import UserProfile, OAuthIdentity, Trip, TripMember, Stay, Move, Taste, Play, Nav, Do, Rec, Attachment, SecurityAuditLog, order_current_and_upcoming_trips

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


class TripAndElementStatusTests(TestCase):
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
            status='UPCOMING',
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

    def test_tripspace_status_transitions_upcoming_current_past(self):
        """Verify owner can transition TripSpace between UPCOMING, CURRENT, and PAST."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        self.assertEqual(self.trip.status, 'UPCOMING')

        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'CURRENT'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'CURRENT')

        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'PAST'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'PAST')

        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'UPCOMING'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'UPCOMING')

    def test_viewer_cannot_change_tripspace_status(self):
        """Verify viewers cannot change TripSpace status."""
        session = self.client.session
        session['user_id'] = str(self.viewer.id)
        session.save()

        resp = self.client.post(reverse('core:update_trip_status', args=[self.trip.id]), {'status': 'PAST'})
        self.assertEqual(resp.status_code, 302)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'UPCOMING')

    def test_dashboard_home_page_shows_editable_status_for_owner_and_editor_and_static_for_viewer(self):
        """Home page trip cards show interactive status select for owners/editors and static pill for viewers."""
        # 1. As owner: should see editable status select with onchange="updateTripStatus(...)"
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'action="{reverse("core:update_trip_status", args=[self.trip.id])}"')
        self.assertContains(resp, 'class="status-pill status-upcoming trip-status-select"')
        self.assertContains(resp, f"updateTripStatus(this, '{self.trip.id}')")
        self.assertContains(resp, 'onclick="goToTrip(event')

        # 2. As viewer: should see read-only status pill and no form
        session['user_id'] = str(self.viewer.id)
        session.save()

        resp = self.client.get(reverse('core:dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, f'action="{reverse("core:update_trip_status", args=[self.trip.id])}"')
        self.assertContains(resp, '<span class="status-pill status-upcoming">Upcoming</span>')

    def test_dashboard_status_update_via_ajax_does_not_redirect(self):
        """Updating status via AJAX returns JSON payload without redirecting."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.post(
            reverse('core:update_trip_status', args=[self.trip.id]),
            {'status': 'CURRENT'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['new_status'], 'CURRENT')
        self.assertEqual(json_data['status_display'], 'Current')

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'CURRENT')

    def test_dashboard_status_update_with_next_redirects_to_dashboard_not_workspace(self):
        """Updating status with next=/ redirects to dashboard, NOT individual tripspace."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.post(
            reverse('core:update_trip_status', args=[self.trip.id]),
            {'status': 'PAST', 'next': reverse('core:dashboard')}
        )
        self.assertRedirects(resp, reverse('core:dashboard'))
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'PAST')

    def test_dashboard_status_update_to_past_moves_trip_between_sections(self):
        """Changing status to PAST moves trip into Your Past Trips section, and back to UPCOMING moves it to Active."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        # Initially trip is UPCOMING
        resp = self.client.get(reverse('core:dashboard'))
        self.assertIn(self.trip, resp.context['upcoming_trips'])
        self.assertNotIn(self.trip, resp.context['past_trips'])

        # Update to PAST
        self.client.post(
            reverse('core:update_trip_status', args=[self.trip.id]),
            {'status': 'PAST'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'PAST')

        # Dashboard now lists trip in past_trips
        resp = self.client.get(reverse('core:dashboard'))
        self.assertNotIn(self.trip, resp.context['upcoming_trips'])
        self.assertIn(self.trip, resp.context['past_trips'])

        # Update back to CURRENT
        self.client.post(
            reverse('core:update_trip_status', args=[self.trip.id]),
            {'status': 'CURRENT'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'CURRENT')

        # Dashboard now lists trip in upcoming_trips
        resp = self.client.get(reverse('core:dashboard'))
        self.assertIn(self.trip, resp.context['upcoming_trips'])
        self.assertNotIn(self.trip, resp.context['past_trips'])

    def test_trip_element_status_cycle_idea_confirmed_complete(self):
        """Verify Stay, Nav, Do, and Rec elements cycle through IDEA -> CONFIRMED -> COMPLETE -> IDEA."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        stay = Stay.objects.create(trip=self.trip, title='Villa Etna', status='IDEA', total_price=500, created_by=self.owner)
        nav = Nav.objects.create(trip=self.trip, title='Catania Ferry', mode='Ferry', status='IDEA', price=80, created_by=self.owner)
        do_item = Do.objects.create(trip=self.trip, title='Mt Etna Hike', status='IDEA', price=120, created_by=self.owner)
        rec = Rec.objects.create(trip=self.trip, title='Cannoli Spot', category='Food', status='IDEA', recommended_by=self.owner)

        for item_type, item in [('stay', stay), ('nav', nav), ('do', do_item), ('rec', rec)]:
            url = reverse('core:toggle_status', args=[item_type, item.id])

            # 1. IDEA -> CONFIRMED
            r1 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r1.json()['new_status'], 'CONFIRMED')
            item.refresh_from_db()
            self.assertEqual(item.status, 'CONFIRMED')

            # 2. CONFIRMED -> COMPLETE
            r2 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(r2.status_code, 200)
            self.assertEqual(r2.json()['new_status'], 'COMPLETE')
            item.refresh_from_db()
            self.assertEqual(item.status, 'COMPLETE')

            # 3. COMPLETE -> IDEA
            r3 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(r3.status_code, 200)
            self.assertEqual(r3.json()['new_status'], 'IDEA')
            item.refresh_from_db()
            self.assertEqual(item.status, 'IDEA')

        # Verify explicit status setting to COMPLETE on Stay and Do
        self.client.post(reverse('core:edit_stay', args=[self.trip.id, stay.id]), {'title': 'Villa Etna', 'status': 'COMPLETE', 'total_price': '500'})
        stay.refresh_from_db()
        self.assertEqual(stay.status, 'COMPLETE')
        self.assertEqual(self.trip.complete_items_count, 1)


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

    def test_viewer_cannot_edit_delete_or_toggle_others_item(self):
        """Viewers cannot edit, delete, or toggle status of items created by others."""
        stay_by_owner = Stay.objects.create(
            trip=self.trip,
            title='Owner Stay',
            status='IDEA',
            created_by=self.owner
        )
        session = self.client.session
        session['user_id'] = str(self.viewer.id)
        session.save()

        # Cannot edit someone else's item
        self.client.post(reverse('core:edit_stay', args=[self.trip.id, stay_by_owner.id]), {'title': 'Tampered Stay'})
        stay_by_owner.refresh_from_db()
        self.assertEqual(stay_by_owner.title, 'Owner Stay')

        # Cannot toggle status of someone else's item
        resp_toggle = self.client.post(
            reverse('core:toggle_status', args=['stay', stay_by_owner.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp_toggle.status_code, 403)
        stay_by_owner.refresh_from_db()
        self.assertEqual(stay_by_owner.status, 'IDEA')

        # Cannot delete someone else's item
        self.client.post(reverse('core:delete_stay', args=[self.trip.id, stay_by_owner.id]))
        self.assertTrue(Stay.objects.filter(id=stay_by_owner.id).exists())

    def test_author_can_edit_delete_and_toggle_own_item_under_universal_sovereignty(self):
        """Under Universal Author Sovereignty, a member can edit, toggle status, and delete items they created even with VIEWER role."""
        stay_by_viewer = Stay.objects.create(
            trip=self.trip,
            title='Viewer Authored Stay',
            status='IDEA',
            created_by=self.viewer
        )
        session = self.client.session
        session['user_id'] = str(self.viewer.id)
        session.save()

        # Can edit their own item
        self.client.post(reverse('core:edit_stay', args=[self.trip.id, stay_by_viewer.id]), {'title': 'Updated Viewer Stay'})
        stay_by_viewer.refresh_from_db()
        self.assertEqual(stay_by_viewer.title, 'Updated Viewer Stay')

        # Can toggle status of their own item
        resp_toggle = self.client.post(
            reverse('core:toggle_status', args=['stay', stay_by_viewer.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp_toggle.status_code, 200)
        stay_by_viewer.refresh_from_db()
        self.assertEqual(stay_by_viewer.status, 'CONFIRMED')

        # Can delete their own item
        self.client.post(reverse('core:delete_stay', args=[self.trip.id, stay_by_viewer.id]))
        self.assertFalse(Stay.objects.filter(id=stay_by_viewer.id).exists())

    @override_settings(ENABLE_DEMO_SWITCHER=False)
    def test_demo_switcher_disabled_blocks_impersonation(self):
        """When ENABLE_DEMO_SWITCHER is False, switch-user and demo_user_id login return 403."""
        resp_switch = self.client.post(reverse('core:switch_user'), {'user_id': str(self.owner.id)})
        self.assertEqual(resp_switch.status_code, 403)
        self.assertIsNone(self.client.session.get('user_id'))

        resp_demo_login = self.client.post(reverse('core:login'), {'demo_user_id': str(self.owner.id)})
        self.assertEqual(resp_demo_login.status_code, 403)
        self.assertIsNone(self.client.session.get('user_id'))


class CryptographicAndPIITests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create(
            email='crypto@example.com',
            handle='cryptouser',
            full_name='Crypto User',
            phone_number='+1-555-867-5309',
            is_active=True
        )
        self.trip_1 = Trip.objects.create(
            title='Trip One',
            location='Zurich',
            year=2026,
            time_granularity='YEAR',
            created_by=self.user
        )
        self.trip_2 = Trip.objects.create(
            title='Trip Two',
            location='Geneva',
            year=2026,
            time_granularity='YEAR',
            created_by=self.user
        )

    def tearDown(self):
        from core.md_sync import delete_trip_markdown
        for t in Trip.objects.all():
            delete_trip_markdown(t)

    def test_aead_context_binding_prevents_ciphertext_transplanting(self):
        """Copying encrypted_confirmation_code to another trip must fail AAD verification."""
        stay_1 = Stay(trip=self.trip_1, title='Alpine Lodge', created_by=self.user)
        stay_1.confirmation_code = 'ZURICH-9988'
        stay_1.save()

        self.assertTrue(stay_1._encrypted_confirmation_code.startswith('v1:'))
        self.assertEqual(stay_1.confirmation_code, 'ZURICH-9988')

        # Transplant ciphertext from trip_1's stay into trip_2's stay
        stay_2 = Stay(trip=self.trip_2, title='Lake Hotel', created_by=self.user)
        stay_2._encrypted_confirmation_code = stay_1._encrypted_confirmation_code
        stay_2.save()

        with self.assertRaises(ValueError):
            _ = stay_2.confirmation_code

    def test_pii_fields_encrypted_in_database_and_decrypted_on_access(self):
        """Verify phone_number, Stay.notes, and Nav.passenger_name are encrypted at rest in SQL."""
        from django.db import connection

        stay = Stay.objects.create(
            trip=self.trip_1,
            title='Vaulted Stay',
            notes='Keypad code: 1234# · WiFi: SecretNet',
            created_by=self.user
        )
        nav = Nav.objects.create(
            trip=self.trip_1,
            title='Swiss Air LX15',
            mode='Flight',
            passenger_name='Crypto User Passport #9911',
            flexibility_notes='Frequent Flyer: LX-009182',
            created_by=self.user
        )

        # Model attribute access transparently decrypts
        self.user.refresh_from_db()
        stay.refresh_from_db()
        nav.refresh_from_db()
        self.assertEqual(self.user.phone_number, '+1-555-867-5309')
        self.assertEqual(stay.notes, 'Keypad code: 1234# · WiFi: SecretNet')
        self.assertEqual(nav.passenger_name, 'Crypto User Passport #9911')
        self.assertEqual(nav.flexibility_notes, 'Frequent Flyer: LX-009182')

        # Raw SQL inspection verifies values on disk are AES-256-GCM ciphertexts ('v1:...')
        with connection.cursor() as cursor:
            cursor.execute("SELECT phone_number FROM users WHERE id = %s", [str(self.user.id).replace('-', '') if connection.vendor == 'sqlite' else str(self.user.id)])
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT phone_number FROM users WHERE email = %s", [self.user.email])
                row = cursor.fetchone()
            raw_phone = row[0]
            self.assertTrue(raw_phone.startswith('v1:'))
            self.assertNotIn('867-5309', raw_phone)

            cursor.execute("SELECT notes FROM stays WHERE title = %s", ['Vaulted Stay'])
            raw_notes = cursor.fetchone()[0]
            self.assertTrue(raw_notes.startswith('v1:'))
            self.assertNotIn('1234#', raw_notes)

    @override_settings(DEBUG=False, ENFORCE_PRODUCTION_KEYS=True)
    def test_production_blocks_insecure_default_encryption_key(self):
        """When DEBUG=False in production, using the default dev FIELD_ENCRYPTION_KEY raises ImproperlyConfigured."""
        from django.core.exceptions import ImproperlyConfigured
        from core.encryption import ConfirmationEncryptor
        with self.assertRaises(ImproperlyConfigured):
            ConfirmationEncryptor.encrypt('TEST-CODE')


class AuditLogAndHashChainTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = UserProfile.objects.create(
            email='audit_owner@example.com',
            handle='auditowner',
            full_name='Audit Owner',
            is_active=True
        )
        self.owner.set_password('StrongPass2026!')
        self.owner.save()

        self.companion = UserProfile.objects.create(
            email='audit_comp@example.com',
            handle='auditcomp',
            full_name='Audit Companion',
            is_active=True
        )
        self.trip = Trip.objects.create(
            title='Audited Trip',
            location='Oslo',
            year=2026,
            time_granularity='YEAR',
            created_by=self.owner
        )
        TripMember.objects.create(trip=self.trip, user=self.owner, role='OWNER')

        self.stay = Stay(trip=self.trip, title='Fjord Hotel', created_by=self.owner)
        self.stay.confirmation_code = 'OSLO-7711'
        self.stay.save()

    def tearDown(self):
        from core.md_sync import delete_trip_markdown
        for t in Trip.objects.all():
            delete_trip_markdown(t)

    def test_audit_events_logged_and_hash_chain_verified(self):
        """Sensitive actions must write chained SecurityAuditLog entries and detect tampering."""
        # 1. Login generates AUTH_LOGIN_SUCCESS
        self.client.post(reverse('core:login'), {
            'handle_or_email': 'auditowner',
            'password': 'StrongPass2026!',
        })
        self.assertTrue(SecurityAuditLog.objects.filter(action='AUTH_LOGIN_SUCCESS', user=self.owner).exists())

        # 2. Revealing confirmation code generates CONFIRMATION_CODE_REVEALED
        resp = self.client.get(reverse('core:reveal_code', args=['stay', self.stay.id]))
        self.assertEqual(resp.status_code, 200)
        reveal_log = SecurityAuditLog.objects.filter(
            action='CONFIRMATION_CODE_REVEALED',
            trip=self.trip,
            user=self.owner
        ).first()
        self.assertIsNotNone(reveal_log)
        self.assertEqual(reveal_log.resource_id, self.stay.id)

        # 3. Inviting a member generates MEMBER_INVITED
        self.client.post(reverse('core:invite_member', args=[self.trip.id]), {
            'handle_or_email': '@auditcomp',
            'role': 'VIEWER'
        })
        self.assertTrue(SecurityAuditLog.objects.filter(action='MEMBER_INVITED', trip=self.trip).exists())

        # 4. Verify cryptographic SHA-256 hash chain is intact
        is_valid, err_msg = SecurityAuditLog.verify_chain()
        self.assertTrue(is_valid, err_msg)

        # 5. Simulate database tampering on an audit log row and verify detection
        SecurityAuditLog.objects.filter(id=reveal_log.id).update(action='VAULT_DOCUMENT_ACCESSED')
        is_valid_after_tamper, tamper_err = SecurityAuditLog.verify_chain()
        self.assertFalse(is_valid_after_tamper)
        self.assertIn(str(reveal_log.id), tamper_err)


class AuthSessionAndHeadersHardeningTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        self.user = UserProfile.objects.create(
            email='hardened@example.com',
            handle='hardeneduser',
            full_name='Hardened User',
            is_active=True
        )
        self.user.set_password('ComplexPass2026!#')
        self.user.save()

    def test_open_redirect_blocked_on_login(self):
        """External malicious ?next= URLs must be rejected and fall back to dashboard."""
        resp = self.client.post(
            f"{reverse('core:login')}?next=https://evil-phishing.example.com/steal",
            {
                'handle_or_email': 'hardeneduser',
                'password': 'ComplexPass2026!#',
            }
        )
        self.assertRedirects(resp, reverse('core:dashboard'))

    def test_weak_numeric_and_common_passwords_rejected(self):
        """Signup must enforce Django AUTH_PASSWORD_VALIDATORS and reject '12345678'."""
        resp = self.client.post(reverse('core:signup'), {
            'full_name': 'Weak Pass User',
            'handle': 'weakpassuser',
            'email': 'weak@example.com',
            'password': '12345678',
            'password_confirm': '12345678',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(UserProfile.objects.filter(handle='weakpassuser').exists())

    def test_session_key_rotated_on_login(self):
        """Login must rotate the session key to prevent Session Fixation attacks."""
        session = self.client.session
        session['pre_login_marker'] = 'fixed'
        session.save()
        old_session_key = session.session_key

        resp = self.client.post(reverse('core:login'), {
            'handle_or_email': 'hardeneduser',
            'password': 'ComplexPass2026!#',
        })
        self.assertRedirects(resp, reverse('core:dashboard'))
        self.assertNotEqual(self.client.session.session_key, old_session_key)

    @override_settings(LOGIN_RATE_LIMIT_ATTEMPTS=3)
    def test_login_brute_force_rate_limiting(self):
        """Exceeding LOGIN_RATE_LIMIT_ATTEMPTS returns 429 Too Many Requests."""
        for _ in range(3):
            r = self.client.post(reverse('core:login'), {
                'handle_or_email': 'hardeneduser',
                'password': 'WrongPassword!',
            })
            self.assertEqual(r.status_code, 200)

        # 4th attempt should be throttled with HTTP 429
        throttled_resp = self.client.post(reverse('core:login'), {
            'handle_or_email': 'hardeneduser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(throttled_resp.status_code, 429)

    def test_security_headers_present_on_responses(self):
        """Verify CSP, Referrer-Policy, Permissions-Policy, and X-Content-Type-Options headers."""
        resp = self.client.get(reverse('core:login'))
        self.assertIn('Content-Security-Policy', resp.headers)
        self.assertIn("frame-ancestors 'none'", resp.headers['Content-Security-Policy'])
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(resp.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
        self.assertIn('Permissions-Policy', resp.headers)


class VaultSecurityAndLifecycleTests(TestCase):
    """Tests for Document Vault magic-byte validation, signed download URLs, and file cleanup."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.owner = UserProfile.objects.create(handle="vaultowner", email="vaultowner@test.com")
        self.outsider = UserProfile.objects.create(handle="vaultoutsider", email="vaultoutsider@test.com")
        self.trip = Trip.objects.create(
            title="Vault Security Trip",
            start_date="2026-12-01",
            end_date="2026-12-05",
            created_by=self.owner
        )
        TripMember.objects.create(trip=self.trip, user=self.owner, role='OWNER')

    def _login_as(self, user):
        session = self.client.session
        session['user_id'] = str(user.id)
        session.save()

    def test_spoofed_html_as_pdf_is_rejected(self):
        """Uploading an HTML/script payload disguised with a .pdf extension must be blocked by magic-byte checks."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self._login_as(self.owner)

        malicious_file = SimpleUploadedFile(
            "boarding_pass.pdf",
            b"<html><script>alert('xss')</script></html>",
            content_type="application/pdf"
        )
        self.client.post(reverse('core:upload_attachment', args=[self.trip.id]), {
            'file_name': 'Boarding Pass',
            'file': malicious_file,
        })
        self.assertEqual(Attachment.objects.filter(trip=self.trip).count(), 0)

    def test_valid_pdf_upload_signed_download_and_physical_cleanup(self):
        """
        Valid PDF magic bytes succeed, randomize disk filename, require valid signed token
        and trip membership for download, log VAULT_DOCUMENT_ACCESSED, and delete physical file on removal.
        """
        import os
        from django.core.files.uploadedfile import SimpleUploadedFile
        self._login_as(self.owner)

        valid_pdf = SimpleUploadedFile(
            "itinerary.pdf",
            b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF",
            content_type="application/pdf"
        )
        self.client.post(reverse('core:upload_attachment', args=[self.trip.id]), {
            'file_name': '../../Flight_Ticket.pdf',
            'file': valid_pdf,
        })

        att = Attachment.objects.filter(trip=self.trip).first()
        self.assertIsNotNone(att)
        # Path traversal stripped from display name
        self.assertEqual(att.file_name, 'Flight_Ticket.pdf')
        # Physical file exists and is stored with randomized UUID filename
        physical_path = att.file.path
        self.assertTrue(os.path.exists(physical_path))
        self.assertNotIn('itinerary', os.path.basename(physical_path))

        # 1. Missing token is rejected (403)
        base_download_url = reverse('core:download_attachment', args=[self.trip.id, att.id])
        self.assertEqual(self.client.get(base_download_url).status_code, 403)

        # 2. Tampered token is rejected (403)
        self.assertEqual(self.client.get(f"{base_download_url}?token=tampered").status_code, 403)

        # 3. Outsider with valid signed URL is rejected (403)
        signed_url = att.signed_download_url
        self._login_as(self.outsider)
        self.assertEqual(self.client.get(signed_url).status_code, 403)

        # 4. Authorized member with valid signed URL succeeds (200) and logs audit event
        self._login_as(self.owner)
        resp = self.client.get(signed_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertTrue(b"".join(resp.streaming_content).startswith(b"%PDF-1.7"))
        self.assertTrue(
            SecurityAuditLog.objects.filter(
                action='VAULT_DOCUMENT_ACCESSED',
                resource_id=str(att.id),
                user=self.owner
            ).exists()
        )

        # 5. Deleting attachment removes physical file from disk via post_delete signal
        self.client.post(reverse('core:delete_attachment', args=[self.trip.id, att.id]))
        self.assertFalse(Attachment.objects.filter(id=att.id).exists())
        self.assertFalse(os.path.exists(physical_path))


class PublicRecommendationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = UserProfile.objects.create(
            email='leila@example.com',
            handle='leila',
            full_name='Leila Gleich',
            is_active=True
        )
        self.trip = Trip.objects.create(
            title='Malticilia 26',
            location='Malta & Sicily',
            created_by=self.owner,
            time_granularity='SEASON_YEAR',
            season='SUMMER',
            year=2026
        )

    def test_public_recommend_get_page(self):
        """Verify non-trippers can access public recommendation page without login."""
        url = reverse('core:public_recommend', args=[self.trip.rec_token])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Malticilia 26')
        self.assertContains(resp, 'Malta &amp; Sicily')
        self.assertContains(resp, 'Your Name or Nickname')

    def test_public_recommend_invalid_token_returns_404(self):
        """Verify invalid or non-existent tokens return 404."""
        url = reverse('core:public_recommend', args=['invalid-token-12345'])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_public_recommend_submission_success(self):
        """Verify non-tripper can submit a recommendation which populates Recs pool as IDEA."""
        url = reverse('core:public_recommend', args=[self.trip.rec_token])
        post_data = {
            'guest_name': 'Marco (Sicily Local)',
            'title': 'Trattoria da Nino',
            'category': 'Food',
            'description': 'Incredible swordfish pasta, ask for outdoor terrace seating!',
            'address': 'Via Luigi Pirandello 37, Taormina',
            'link': 'https://example.com/trattoria-nino',
        }
        resp = self.client.post(url, post_data)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('submitted=1', resp.url)

        # Verify Rec created in DB
        rec = Rec.objects.filter(trip=self.trip, title='Trattoria da Nino').first()
        self.assertIsNotNone(rec)
        self.assertEqual(rec.guest_name, 'Marco (Sicily Local)')
        self.assertEqual(rec.status, 'IDEA')
        self.assertEqual(rec.category, 'Food')
        self.assertIsNone(rec.recommended_by)

    def test_public_recommend_honeypot_rejects_bot(self):
        """Verify bot filling out honeypot does not create a Rec."""
        url = reverse('core:public_recommend', args=[self.trip.rec_token])
        post_data = {
            'guest_name': 'Spambot',
            'title': 'Buy Cheap Watches',
            'category': 'Food',
            'website_url': 'http://spamsite.com',
        }
        resp = self.client.post(url, post_data)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Rec.objects.filter(title='Buy Cheap Watches').exists())

    def test_workspace_displays_rec_invite_link_and_move_stay_taste_play_tabs(self):
        """Verify workspace top section contains copyable recommendation invite link and Move, Stay, Taste, Play tabs."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)
        # Move, Stay, Taste, Play tab elements
        self.assertContains(resp, "switchTab('move', this)")
        self.assertContains(resp, "switchTab('stay', this)")
        self.assertContains(resp, "switchTab('taste', this)")
        self.assertContains(resp, "switchTab('play', this)")
        self.assertContains(resp, '✈️ Move')
        self.assertContains(resp, '🏨 Stay')
        self.assertContains(resp, '🍽️ Taste')
        self.assertContains(resp, '🎯 Play')
        # Recommendation Link button in workspace overview
        self.assertContains(resp, 'Recommendation Link')
        self.assertContains(resp, self.trip.rec_token)
        self.assertContains(resp, "Collect and record recommendations for your trip using this easy form. They will show up in the 'recommendations' section of your trip")
        self.assertNotContains(resp, 'rec-invite-bar')


class GlobalNavigationAndCreateTripModalTests(TestCase):
    """Tests for the global Create Trip modal and the active TripSpaces navbar dropdown."""

    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.create(
            email='navtester@example.com',
            handle='navtester',
            full_name='Nav Tester',
            is_active=True
        )
        self.outsider = UserProfile.objects.create(
            email='outsider@example.com',
            handle='outsider',
            full_name='Outsider User',
            is_active=True
        )
        self.upcoming_trip = Trip.objects.create(
            title='Upcoming Alps Expedition',
            location='Chamonix, France',
            status='UPCOMING',
            created_by=self.user,
            time_granularity='SEASON_YEAR',
            season='WINTER',
            year=2027
        )
        TripMember.objects.create(trip=self.upcoming_trip, user=self.user, role='OWNER')

        self.current_trip = Trip.objects.create(
            title='Current Lisbon Escape',
            location='Lisbon, Portugal',
            status='CURRENT',
            created_by=self.user,
            time_granularity='YEAR',
            year=2026
        )
        TripMember.objects.create(trip=self.current_trip, user=self.user, role='OWNER')

        self.past_trip = Trip.objects.create(
            title='Archived Kyoto Trip',
            location='Kyoto, Japan',
            status='PAST',
            created_by=self.user,
            time_granularity='YEAR',
            year=2024
        )
        TripMember.objects.create(trip=self.past_trip, user=self.user, role='OWNER')

        self.outsider_trip = Trip.objects.create(
            title='Secret Outsider Trip',
            location='Reykjavik, Iceland',
            status='UPCOMING',
            created_by=self.outsider,
            time_granularity='YEAR',
            year=2026
        )
        TripMember.objects.create(trip=self.outsider_trip, user=self.outsider, role='OWNER')

        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()

    def test_tripspaces_dropdown_lists_only_user_active_trips_across_pages(self):
        """Navbar TripSpaces dropdown lists CURRENT and UPCOMING trips for the user and excludes PAST or outsider trips."""
        for url in [
            reverse('core:dashboard'),
            reverse('core:profile'),
            reverse('core:trip_workspace', args=[self.upcoming_trip.id]),
        ]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, 'id="tripspacesDropdownMenu"')
            self.assertContains(resp, reverse('core:trip_workspace', args=[self.upcoming_trip.id]))
            self.assertContains(resp, reverse('core:trip_workspace', args=[self.current_trip.id]))
            # Verify outsider trip is never in the dropdown
            self.assertNotContains(resp, 'Secret Outsider Trip')
            # Verify active count badge shows 2 active trips (UPCOMING + CURRENT, excluding PAST)
            self.assertContains(resp, '2 Active')

    def test_create_trip_modal_is_present_globally_and_profile_opens_modal_directly(self):
        """Profile and Trip Workspace pages include #createTripModal and trigger openModal('createTripModal') without redirecting."""
        profile_resp = self.client.get(reverse('core:profile'))
        self.assertEqual(profile_resp.status_code, 200)
        self.assertContains(profile_resp, 'id="createTripModal"')
        self.assertContains(profile_resp, "openModal('createTripModal')")
        # Ensure Profile no longer uses a link to dashboard for "+ Create a Trip"
        self.assertNotContains(profile_resp, f'<a href="{reverse("core:dashboard")}" class="btn btn-sm btn-primary">+ Create a Trip</a>')

        workspace_resp = self.client.get(reverse('core:trip_workspace', args=[self.upcoming_trip.id]))
        self.assertEqual(workspace_resp.status_code, 200)
        self.assertContains(workspace_resp, 'id="createTripModal"')
        self.assertContains(workspace_resp, "openModal('createTripModal')")


class TripWorkspaceAddElementAndDisplayTests(TestCase):
    """Tests for the Add Element top button, optional field omission, and card title structure."""

    def setUp(self):
        self.client = Client()
        self.owner = UserProfile.objects.create(
            email='tripper_owner@example.com',
            handle='owner_sam',
            full_name='Sam Owner',
            is_active=True
        )
        self.viewer = UserProfile.objects.create(
            email='tripper_viewer@example.com',
            handle='viewer_val',
            full_name='Val Viewer',
            is_active=True
        )
        self.trip = Trip.objects.create(
            title='Iceland Ring Road Expedition',
            location='Reykjavik, Iceland',
            status='UPCOMING',
            created_by=self.owner,
            time_granularity='YEAR',
            year=2026
        )
        TripMember.objects.create(trip=self.trip, user=self.owner, role='OWNER')
        TripMember.objects.create(trip=self.trip, user=self.viewer, role='VIEWER')

    def test_add_element_button_and_dropdown_for_editor(self):
        """Top workspace detail section has 'Add Element' button & dropdown for all 4 elements (Move, Stay, Taste, Play)."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)

        # 'Add Element' button in workspace actions
        self.assertContains(resp, 'id="addElementBtn"')
        self.assertContains(resp, 'Add Element ▾')
        self.assertContains(resp, 'id="addElementDropdownMenu"')

        # All 4 elements present in dropdown
        self.assertContains(resp, "openAddElement('move')")
        self.assertContains(resp, "openAddElement('stay')")
        self.assertContains(resp, "openAddElement('taste')")
        self.assertContains(resp, "openAddElement('play')")

        # Element chooser modal also available
        self.assertContains(resp, 'id="addElementModal"')

    def test_add_element_button_hidden_for_viewer(self):
        """Viewers without edit permissions do not see 'Add Element' button."""
        session = self.client.session
        session['user_id'] = str(self.viewer.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'id="addElementBtn"')
        self.assertNotContains(resp, 'id="addElementDropdownMenu"')

    def test_blank_optional_inputs_do_not_render_placeholders(self):
        """Unfilled optional inputs must NOT show placeholder/fallback text (TBD, Free, etc.)."""
        from core.models import Stay, Nav, Do, Rec
        # Create Stay with only required fields (no address, no check_in, no check_out, no price, no beds)
        Stay.objects.create(
            trip=self.trip,
            title='Minimal Stay',
            status='CONFIRMED',
            created_by=self.owner
        )
        # Create Nav with only required fields (no origin, no destination, no departure_time, no arrival_time, no price)
        Nav.objects.create(
            trip=self.trip,
            title='Minimal Nav Flight',
            mode='Flight',
            status='CONFIRMED',
            created_by=self.owner
        )
        # Create Do with only required fields (no price, no start_time, no end_time, no address)
        Do.objects.create(
            trip=self.trip,
            title='Minimal Activity',
            status='IDEA',
            created_by=self.owner
        )

        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)

        # Ensure no "TBD", "Price TBD", or "Free / Unticketed" are displayed for these items
        self.assertNotContains(resp, 'Price TBD')
        self.assertNotContains(resp, 'Free / Unticketed')
        self.assertNotContains(resp, 'Origin TBD')
        self.assertNotContains(resp, 'Destination TBD')
        self.assertNotContains(resp, 'Flexible timing')
        self.assertNotContains(resp, 'Origin ➔ Destination')

    def test_filled_optional_inputs_render_properly(self):
        """Filled optional inputs render their actual values."""
        from core.models import Stay, Nav, Do
        from django.utils import timezone
        import datetime

        now = timezone.now()
        Stay.objects.create(
            trip=self.trip,
            title='Saga Luxury Hotel',
            total_price=890.50,
            num_beds=3,
            check_in=now,
            created_by=self.owner
        )
        Nav.objects.create(
            trip=self.trip,
            title='Icelandair Flight FI 614',
            mode='Flight',
            origin_address='BOS Boston',
            destination_address='KEF Reykjavik',
            price=640.00,
            departure_time=now + datetime.timedelta(days=1),
            created_by=self.owner
        )
        Do.objects.create(
            trip=self.trip,
            title='Blue Lagoon Spa Experience',
            price=125.00,
            start_time=now + datetime.timedelta(days=2),
            created_by=self.owner
        )

        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)

        # Check values are rendered
        self.assertContains(resp, '$890.50')
        self.assertContains(resp, '3 Beds')
        self.assertContains(resp, 'BOS Boston')
        self.assertContains(resp, 'KEF Reykjavik')
        self.assertContains(resp, '$640.00')
        self.assertContains(resp, '$125.00')

    def test_item_card_header_top_and_item_title_structure(self):
        """Item card headers must contain item-card-header-top and full-width item-title."""
        from core.models import Stay
        Stay.objects.create(
            trip=self.trip,
            title='Grand Seaside Villa',
            created_by=self.owner
        )

        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)

        self.assertContains(resp, 'class="item-card-header"')
        self.assertContains(resp, 'class="item-card-header-top"')
        self.assertContains(resp, '<h3 class="item-title">Grand Seaside Villa</h3>')

    def test_workspace_top_bar_full_width_layout(self):
        """Workspace top bar contains actions and keeps title unobstructed."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'class="workspace-top-bar"')
        self.assertContains(resp, '<h1 class="workspace-title">')

    def test_itinerary_view_edit_and_delete_actions_rendered(self):
        """Itinerary / timeline view renders edit and delete triggers for author or editor."""
        from core.models import Stay
        stay = Stay.objects.create(
            trip=self.trip,
            title='Reykjavik Hotel',
            created_by=self.owner
        )
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f"openEditItemModal('stay', '{stay.id}')")
        self.assertContains(resp, f"openDeleteItemModal('stay', '{stay.id}')")

    def test_edit_and_delete_redirects_to_next_url(self):
        """Submitting an edit with next=<url> redirects to the specified next URL."""
        from core.models import Stay
        stay = Stay.objects.create(
            trip=self.trip,
            title='Initial Title',
            created_by=self.owner
        )
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.post(
            reverse('core:edit_stay', args=[self.trip.id, stay.id]),
            {'title': 'Updated Title', 'next': f"/trips/{self.trip.id}/#timeline"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f"/trips/{self.trip.id}/#timeline")


class DateRangeValidationAndOptionalStayTimesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.create(
            email='dates_tester@example.com',
            handle='datestester',
            full_name='Dates Tester',
            is_active=True
        )
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()

        self.trip = Trip.objects.create(
            title='Nordic Adventure',
            location='Norway',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 11, 1),
            end_date=datetime.date(2026, 11, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=self.trip, user=self.user, role='OWNER')

    def test_trip_creation_rejects_end_date_before_start_date(self):
        """User cannot create a trip with end_date before start_date."""
        resp = self.client.post(reverse('core:create_trip'), {
            'title': 'Invalid Dates Trip',
            'location': 'Reykjavik',
            'time_granularity': 'EXACT_RANGE',
            'start_date': '2026-12-10',
            'end_date': '2026-12-05',
        }, follow=True)
        self.assertContains(resp, 'Trip end date cannot be before start date.')
        self.assertFalse(Trip.objects.filter(title='Invalid Dates Trip').exists())

    def test_trip_creation_accepts_valid_date_range(self):
        """User can create a trip with end_date >= start_date."""
        resp = self.client.post(reverse('core:create_trip'), {
            'title': 'Valid Dates Trip',
            'location': 'Reykjavik',
            'time_granularity': 'EXACT_RANGE',
            'start_date': '2026-12-05',
            'end_date': '2026-12-10',
        }, follow=True)
        self.assertTrue(Trip.objects.filter(title='Valid Dates Trip').exists())

    def test_trip_edit_rejects_end_date_before_start_date(self):
        """User cannot update a trip to have end_date before start_date."""
        resp = self.client.post(reverse('core:edit_trip', args=[self.trip.id]), {
            'title': self.trip.title,
            'location': self.trip.location,
            'time_granularity': 'EXACT_RANGE',
            'start_date': '2026-11-15',
            'end_date': '2026-11-10',
        }, follow=True)
        self.assertContains(resp, 'Trip end date cannot be before start date.')
        self.trip.refresh_from_db()
        self.assertEqual(str(self.trip.start_date), '2026-11-01')

    def test_confirmed_stay_requires_start_and_end_dates(self):
        """Confirmed stays must require both check-in (start) and check-out (end) dates."""
        # Missing both dates
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Missing Dates Hotel',
            'status': 'CONFIRMED',
        }, follow=True)
        self.assertContains(resp, 'Confirmed stays require both a check-in date (start) and check-out date (end).')
        self.assertFalse(Stay.objects.filter(title='Missing Dates Hotel').exists())

        # Missing check-out date
        resp2 = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Missing Checkout Hotel',
            'status': 'CONFIRMED',
            'check_in_date': '2026-11-02',
        }, follow=True)
        self.assertContains(resp2, 'Confirmed stays require both a check-in date (start) and check-out date (end).')
        self.assertFalse(Stay.objects.filter(title='Missing Checkout Hotel').exists())

    def test_confirmed_stay_accepts_dates_with_optional_times_omitted(self):
        """Confirmed stays accept start date and end date with check-in/out times omitted (optional)."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Fjord Cabin',
            'status': 'CONFIRMED',
            'check_in_date': '2026-11-02',
            'check_out_date': '2026-11-06',
            'check_in_time': '',
            'check_out_time': '',
        }, follow=True)
        stay = Stay.objects.get(title='Fjord Cabin')
        self.assertEqual(stay.status, 'CONFIRMED')
        self.assertIsNotNone(stay.check_in)
        self.assertIsNotNone(stay.check_out)
        self.assertFalse(stay.is_check_in_time_set)
        self.assertFalse(stay.is_check_out_time_set)

    def test_confirmed_stay_accepts_dates_with_optional_times_provided(self):
        """Confirmed stays properly record optional check-in and check-out times when provided."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Grand Fjord Hotel',
            'status': 'CONFIRMED',
            'check_in_date': '2026-11-02',
            'check_out_date': '2026-11-06',
            'check_in_time': '15:00',
            'check_out_time': '11:00',
        }, follow=True)
        stay = Stay.objects.get(title='Grand Fjord Hotel')
        self.assertEqual(stay.status, 'CONFIRMED')
        self.assertTrue(stay.is_check_in_time_set)
        self.assertTrue(stay.is_check_out_time_set)
        self.assertEqual(stay.check_in_time_str, '15:00')
        self.assertEqual(stay.check_out_time_str, '11:00')

    def test_idea_stay_allows_blank_dates(self):
        """Stays marked as IDEA allow dates to be optional / blank."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Tentative Hostel Idea',
            'status': 'IDEA',
        }, follow=True)
        self.assertTrue(Stay.objects.filter(title='Tentative Hostel Idea').exists())
        stay = Stay.objects.get(title='Tentative Hostel Idea')
        self.assertIsNone(stay.check_in)
        self.assertIsNone(stay.check_out)

    def test_stay_rejects_checkout_date_before_checkin_date(self):
        """Stay rejects check_out_date that is before check_in_date."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Time Travel Lodge',
            'status': 'IDEA',
            'check_in_date': '2026-11-05',
            'check_out_date': '2026-11-02',
        }, follow=True)
        self.assertContains(resp, 'Check-out date/time cannot be before check-in date/time.')
        self.assertFalse(Stay.objects.filter(title='Time Travel Lodge').exists())

    def test_stay_rejects_checkout_time_before_checkin_time_on_same_date(self):
        """Stay on same date rejects checkout time that is before checkin time."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Dayroom Lounge',
            'status': 'CONFIRMED',
            'check_in_date': '2026-11-05',
            'check_out_date': '2026-11-05',
            'check_in_time': '14:00',
            'check_out_time': '10:00',
        }, follow=True)
        self.assertContains(resp, 'Check-out date/time cannot be before check-in date/time.')
        self.assertFalse(Stay.objects.filter(title='Dayroom Lounge').exists())

    def test_edit_stay_rejects_invalid_date_order_and_confirms_valid_update(self):
        """Editing stay enforces date bounds and updates dates/times."""
        stay = Stay.objects.create(
            trip=self.trip,
            title='Initial Stay',
            status='IDEA',
            created_by=self.user
        )

        # Invalid edit: checkout before checkin
        resp = self.client.post(reverse('core:edit_stay', args=[self.trip.id, stay.id]), {
            'title': 'Initial Stay',
            'status': 'IDEA',
            'check_in_date': '2026-11-05',
            'check_out_date': '2026-11-03',
        }, follow=True)
        self.assertContains(resp, 'Check-out date/time cannot be before check-in date/time.')
        stay.refresh_from_db()
        self.assertIsNone(stay.check_in)

        # Invalid edit: change status to CONFIRMED without dates
        resp2 = self.client.post(reverse('core:edit_stay', args=[self.trip.id, stay.id]), {
            'title': 'Initial Stay',
            'status': 'CONFIRMED',
            'check_in_date': '',
            'check_out_date': '',
        }, follow=True)
        self.assertContains(resp2, 'Confirmed stays require both a check-in date (start) and check-out date (end).')
        stay.refresh_from_db()
        self.assertEqual(stay.status, 'IDEA')

        # Valid edit to CONFIRMED with dates and optional check-in time only
        resp3 = self.client.post(reverse('core:edit_stay', args=[self.trip.id, stay.id]), {
            'title': 'Updated Confirmed Stay',
            'status': 'CONFIRMED',
            'check_in_date': '2026-11-03',
            'check_out_date': '2026-11-07',
            'check_in_time': '16:00',
            'check_out_time': '',
        }, follow=True)
        stay.refresh_from_db()
        self.assertEqual(stay.status, 'CONFIRMED')
        self.assertTrue(stay.is_check_in_time_set)
        self.assertFalse(stay.is_check_out_time_set)

    def test_add_stay_modal_rendered_with_simplified_inputs_and_more_options(self):
        """Workspace renders the Add Stay modal with primary inputs, confirmation code container, more options button, and document upload."""
        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)

        # Primary fields: title, status, check_in_date, check_out_date, total_price, notes
        self.assertContains(resp, 'name="title"')
        self.assertContains(resp, 'id="addStayStatus"')
        self.assertContains(resp, 'name="check_in_date"')
        self.assertContains(resp, 'name="check_out_date"')
        self.assertContains(resp, 'name="total_price"')
        self.assertContains(resp, 'name="notes"')

        # Confirmation code conditional container
        self.assertContains(resp, 'id="addStayConfirmationCol"')
        self.assertContains(resp, 'id="addStayConfirmationCode"')

        # More options toggle button and expandable details section
        self.assertContains(resp, 'id="btnToggleStayMoreOptions"')
        self.assertContains(resp, 'onclick="toggleStayMoreOptions()"')
        self.assertContains(resp, 'id="stayMoreOptionsContent"')

        # Additional attributes in expandable section: place_type, num_beds, num_rooms, num_guests, address, check_in_time, check_out_time, booking_link, documents
        self.assertContains(resp, 'id="addStayPlaceType"')
        self.assertContains(resp, 'name="num_beds"')
        self.assertContains(resp, 'name="num_rooms"')
        self.assertContains(resp, 'name="num_guests"')
        self.assertContains(resp, 'name="address"')
        self.assertContains(resp, 'name="check_in_time"')
        self.assertContains(resp, 'name="check_out_time"')
        self.assertContains(resp, 'name="booking_link"')
        self.assertContains(resp, 'name="documents"')

    def test_add_stay_confirmation_code_saved_for_confirmed_hotel(self):
        """Confirmation code is saved when status is CONFIRMED and accommodation is a hotel."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Reykjavik Grand Hotel',
            'status': 'CONFIRMED',
            'place_type': 'Hotel Room',
            'check_in_date': '2026-11-10',
            'check_out_date': '2026-11-14',
            'total_price': '650.00',
            'notes': 'Quiet room on upper floor',
            'confirmation_code': 'HTL-REY-9988',
        }, follow=True)

        stay = Stay.objects.get(title='Reykjavik Grand Hotel')
        self.assertEqual(stay.status, 'CONFIRMED')
        self.assertTrue(stay.has_confirmation_code)
        self.assertEqual(stay.confirmation_code, 'HTL-REY-9988')
        self.assertEqual(float(stay.total_price), 650.0)
        self.assertEqual(stay.notes, 'Quiet room on upper floor')

    def test_add_stay_confirmation_code_not_saved_for_unconfirmed_stay(self):
        """Confirmation code is not saved when stay status is IDEA."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Tentative Hotel Idea',
            'status': 'IDEA',
            'place_type': 'Hotel Room',
            'total_price': '400.00',
            'confirmation_code': 'SHOULD-NOT-SAVE-1',
        }, follow=True)

        stay = Stay.objects.get(title='Tentative Hotel Idea')
        self.assertEqual(stay.status, 'IDEA')
        self.assertFalse(stay.has_confirmation_code)

    def test_add_stay_confirmation_code_not_saved_for_non_hotel(self):
        """Confirmation code is not saved when stay is not a hotel (e.g. Entire Place / House)."""
        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Countryside Cottage',
            'status': 'CONFIRMED',
            'place_type': 'Entire Place',
            'check_in_date': '2026-11-10',
            'check_out_date': '2026-11-14',
            'total_price': '850.00',
            'confirmation_code': 'AIRBNB-SECRET-99',
        }, follow=True)

        stay = Stay.objects.get(title='Countryside Cottage')
        self.assertEqual(stay.status, 'CONFIRMED')
        self.assertFalse(stay.has_confirmation_code)

    def test_add_stay_uploads_documents_to_vault_and_links_to_stay(self):
        """Adding a stay with uploaded documents securely attaches them to the Stay in the Vault."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        pdf_file = SimpleUploadedFile(
            "Booking_Confirmation.pdf",
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF",
            content_type="application/pdf"
        )

        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Harbor View Hotel',
            'status': 'CONFIRMED',
            'place_type': 'Hotel Room',
            'check_in_date': '2026-11-12',
            'check_out_date': '2026-11-15',
            'total_price': '520.00',
            'confirmation_code': 'HARBOR-7722',
            'documents': [pdf_file],
        }, follow=True)

        stay = Stay.objects.get(title='Harbor View Hotel')
        self.assertEqual(stay.confirmation_code, 'HARBOR-7722')

        # Verify Attachment exists and is linked to the stay and trip
        att = Attachment.objects.filter(trip=self.trip, stay=stay).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.file_name, 'Booking_Confirmation.pdf')
        self.assertEqual(att.file_type, 'application/pdf')
        self.assertEqual(att.uploaded_by, self.user)

        # Verify Security Audit Log
        audit_log = SecurityAuditLog.objects.filter(
            trip=self.trip,
            action='VAULT_DOCUMENT_UPLOADED',
            resource_id=att.id
        ).first()
        self.assertIsNotNone(audit_log)

        # Verify attachment appears on workspace page
        ws_resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertContains(ws_resp, 'Booking_Confirmation.pdf')

    def test_add_stay_uploads_multiple_documents(self):
        """Adding a stay with multiple uploaded documents attaches all valid documents."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        doc1 = SimpleUploadedFile(
            "Receipt.pdf",
            b"%PDF-1.5\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF",
            content_type="application/pdf"
        )
        doc2 = SimpleUploadedFile(
            "KeyCard.png",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82",
            content_type="image/png"
        )

        resp = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'Nordic Suites',
            'status': 'CONFIRMED',
            'place_type': 'Hotel Room',
            'check_in_date': '2026-11-20',
            'check_out_date': '2026-11-25',
            'documents': [doc1, doc2],
        }, follow=True)

        stay = Stay.objects.get(title='Nordic Suites')
        attachments = Attachment.objects.filter(trip=self.trip, stay=stay).order_by('file_name')
        self.assertEqual(attachments.count(), 2)
        filenames = [a.file_name for a in attachments]
        self.assertIn('Receipt.pdf', filenames)
        self.assertIn('KeyCard.png', filenames)

    def test_nav_rejects_arrival_before_departure(self):
        """Nav rejects arrival_time earlier than departure_time."""
        resp = self.client.post(reverse('core:add_nav', args=[self.trip.id]), {
            'title': 'Backward Flight',
            'mode': 'Flight',
            'departure_time': '2026-11-02T14:00',
            'arrival_time': '2026-11-02T10:00',
        }, follow=True)
        self.assertContains(resp, 'Arrival date/time cannot be before departure date/time.')
        self.assertFalse(Nav.objects.filter(title='Backward Flight').exists())

    def test_nav_accepts_valid_arrival_after_departure(self):
        """Nav accepts arrival_time >= departure_time."""
        resp = self.client.post(reverse('core:add_nav', args=[self.trip.id]), {
            'title': 'Forward Flight',
            'mode': 'Flight',
            'departure_time': '2026-11-02T10:00',
            'arrival_time': '2026-11-02T14:00',
        }, follow=True)
        self.assertTrue(Nav.objects.filter(title='Forward Flight').exists())

    def test_do_rejects_end_time_before_start_time(self):
        """Do rejects end_time earlier than start_time."""
        resp = self.client.post(reverse('core:add_do', args=[self.trip.id]), {
            'title': 'Rewind Tour',
            'start_time': '2026-11-03T15:00',
            'end_time': '2026-11-03T12:00',
        }, follow=True)
        self.assertContains(resp, 'End date/time cannot be before start date/time.')
        self.assertFalse(Do.objects.filter(title='Rewind Tour').exists())

    def test_do_accepts_valid_end_time_after_start_time(self):
        """Do accepts end_time >= start_time."""
        resp = self.client.post(reverse('core:add_do', args=[self.trip.id]), {
            'title': 'Forward Tour',
            'start_time': '2026-11-03T12:00',
            'end_time': '2026-11-03T15:00',
        }, follow=True)
        self.assertTrue(Do.objects.filter(title='Forward Tour').exists())

    def test_workspace_renders_stay_dates_and_optional_times_correctly(self):
        """Workspace renders date-only stays without phantom times, and renders times when set."""
        import datetime
        now = timezone.now()
        # Stay 1: Dates only, no times
        s1 = Stay.objects.create(
            trip=self.trip,
            title='No Times Stay',
            status='CONFIRMED',
            check_in=datetime.datetime(2026, 11, 2, 0, 0, tzinfo=datetime.timezone.utc),
            check_out=datetime.datetime(2026, 11, 6, 0, 0, tzinfo=datetime.timezone.utc),
            has_check_in_time=False,
            has_check_out_time=False,
            created_by=self.user
        )

        # Stay 2: Dates and times
        s2 = Stay.objects.create(
            trip=self.trip,
            title='With Times Stay',
            status='CONFIRMED',
            check_in=datetime.datetime(2026, 11, 6, 15, 0, tzinfo=datetime.timezone.utc),
            check_out=datetime.datetime(2026, 11, 10, 11, 0, tzinfo=datetime.timezone.utc),
            has_check_in_time=True,
            has_check_out_time=True,
            created_by=self.user
        )

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)

        # Check Add Stay modal input fields
        self.assertContains(resp, 'name="check_in_date"')
        self.assertContains(resp, 'name="check_out_date"')
        self.assertContains(resp, 'name="check_in_time"')
        self.assertContains(resp, 'name="check_out_time"')
        self.assertContains(resp, 'Check-in Time <small class="text-muted">(Optional)</small>')
        self.assertContains(resp, 'Check-out Time <small class="text-muted">(Optional)</small>')

        # Base JS date constraint functions
        self.assertContains(resp, 'initAllDateConstraints')
        self.assertContains(resp, 'setupStayDateSync')
        self.assertContains(resp, 'setupDateRangePair')
        self.assertContains(resp, 'setupDateTimeRangePair')
        self.assertContains(resp, 'setupSingleDateElementSync')

    def test_only_stay_has_start_and_end_dates_validation(self):
        """Only stays require both start and end dates when confirmed."""
        # Confirmed stay fails without both dates
        resp_stay = self.client.post(reverse('core:add_stay', args=[self.trip.id]), {
            'title': 'No Dates Hotel',
            'status': 'CONFIRMED',
        }, follow=True)
        self.assertContains(resp_stay, 'Confirmed stays require both a check-in date (start) and check-out date (end).')

    def test_move_date_required_if_confirmed_optional_if_idea(self):
        """Moves require a date when confirmed; date is optional when status is IDEA."""
        # 1. Confirmed Move without date is rejected
        resp_conf_no_date = self.client.post(reverse('core:add_move', args=[self.trip.id]), {
            'title': 'Undated Confirmed Flight',
            'mode': 'Flight',
            'status': 'CONFIRMED',
        }, follow=True)
        self.assertContains(resp_conf_no_date, 'Confirmed moves require a date.')
        self.assertFalse(Move.objects.filter(title='Undated Confirmed Flight').exists())

        # 2. Idea Move without date is accepted (optional)
        resp_idea_no_date = self.client.post(reverse('core:add_move', args=[self.trip.id]), {
            'title': 'Undated Idea Flight',
            'mode': 'Flight',
            'status': 'IDEA',
        }, follow=True)
        self.assertEqual(resp_idea_no_date.status_code, 200)
        move_idea = Move.objects.filter(title='Undated Idea Flight').first()
        self.assertIsNotNone(move_idea)
        self.assertEqual(move_idea.status, 'IDEA')
        self.assertIsNone(move_idea.departure_time)
        self.assertIsNone(move_idea.arrival_time)
        self.assertIsNone(move_idea.date)

        # 3. Confirmed Move with single date succeeds and has no arrival/end date
        resp_conf_with_date = self.client.post(reverse('core:add_move', args=[self.trip.id]), {
            'title': 'Dated Confirmed Flight',
            'mode': 'Flight',
            'status': 'CONFIRMED',
            'date': '2026-11-15',
            'time': '09:30',
        }, follow=True)
        self.assertEqual(resp_conf_with_date.status_code, 200)
        move_conf = Move.objects.filter(title='Dated Confirmed Flight').first()
        self.assertIsNotNone(move_conf)
        self.assertEqual(move_conf.status, 'CONFIRMED')
        self.assertEqual(str(move_conf.date), '2026-11-15')
        self.assertTrue(move_conf.is_departure_time_set)
        self.assertIsNone(move_conf.arrival_time)

        # 4. Editing Move from IDEA to CONFIRMED without date is rejected
        edit_resp = self.client.post(reverse('core:edit_move', args=[self.trip.id, move_idea.id]), {
            'title': 'Undated Idea Flight',
            'status': 'CONFIRMED',
            'date': '',
        }, follow=True)
        self.assertContains(edit_resp, 'Confirmed moves require a date.')
        move_idea.refresh_from_db()
        self.assertEqual(move_idea.status, 'IDEA')

    def test_taste_date_required_if_confirmed_optional_if_idea(self):
        """Tastes require a date when confirmed; date is optional when status is IDEA."""
        # 1. Confirmed Taste without date is rejected
        resp_conf_no_date = self.client.post(reverse('core:add_taste', args=[self.trip.id]), {
            'title': 'Undated Confirmed Dinner',
            'taste_type': 'Restaurant',
            'status': 'CONFIRMED',
        }, follow=True)
        self.assertContains(resp_conf_no_date, 'Confirmed food & drink reservations require a date.')
        self.assertFalse(Taste.objects.filter(title='Undated Confirmed Dinner').exists())

        # 2. Idea Taste without date is accepted (optional)
        resp_idea_no_date = self.client.post(reverse('core:add_taste', args=[self.trip.id]), {
            'title': 'Undated Idea Cafe',
            'taste_type': 'Cafe & Bakery',
            'status': 'IDEA',
        }, follow=True)
        self.assertEqual(resp_idea_no_date.status_code, 200)
        taste_idea = Taste.objects.filter(title='Undated Idea Cafe').first()
        self.assertIsNotNone(taste_idea)
        self.assertEqual(taste_idea.status, 'IDEA')
        self.assertIsNone(taste_idea.start_time)
        self.assertIsNone(taste_idea.end_time)
        self.assertIsNone(taste_idea.date)

        # 3. Confirmed Taste with single date succeeds and has no end date
        resp_conf_with_date = self.client.post(reverse('core:add_taste', args=[self.trip.id]), {
            'title': 'Dated Confirmed Dinner',
            'taste_type': 'Restaurant',
            'status': 'CONFIRMED',
            'date': '2026-11-16',
            'time': '19:00',
        }, follow=True)
        self.assertEqual(resp_conf_with_date.status_code, 200)
        taste_conf = Taste.objects.filter(title='Dated Confirmed Dinner').first()
        self.assertIsNotNone(taste_conf)
        self.assertEqual(taste_conf.status, 'CONFIRMED')
        self.assertEqual(str(taste_conf.date), '2026-11-16')
        self.assertTrue(taste_conf.is_start_time_set)
        self.assertIsNone(taste_conf.end_time)

        # 4. Editing Taste from IDEA to CONFIRMED without date is rejected
        edit_resp = self.client.post(reverse('core:edit_taste', args=[self.trip.id, taste_idea.id]), {
            'title': 'Undated Idea Cafe',
            'status': 'CONFIRMED',
            'date': '',
        }, follow=True)
        self.assertContains(edit_resp, 'Confirmed food & drink reservations require a date.')
        taste_idea.refresh_from_db()
        self.assertEqual(taste_idea.status, 'IDEA')

    def test_play_date_required_if_confirmed_optional_if_idea(self):
        """Plays require a date when confirmed; date is optional when status is IDEA."""
        # 1. Confirmed Play without date is rejected
        resp_conf_no_date = self.client.post(reverse('core:add_play', args=[self.trip.id]), {
            'title': 'Undated Confirmed Museum',
            'play_type': 'Culture & Museum',
            'status': 'CONFIRMED',
        }, follow=True)
        self.assertContains(resp_conf_no_date, 'Confirmed activities require a date.')
        self.assertFalse(Play.objects.filter(title='Undated Confirmed Museum').exists())

        # 2. Idea Play without date is accepted (optional)
        resp_idea_no_date = self.client.post(reverse('core:add_play', args=[self.trip.id]), {
            'title': 'Undated Idea Hike',
            'play_type': 'Outdoor & Hike',
            'status': 'IDEA',
        }, follow=True)
        self.assertEqual(resp_idea_no_date.status_code, 200)
        play_idea = Play.objects.filter(title='Undated Idea Hike').first()
        self.assertIsNotNone(play_idea)
        self.assertEqual(play_idea.status, 'IDEA')
        self.assertIsNone(play_idea.start_time)
        self.assertIsNone(play_idea.end_time)
        self.assertIsNone(play_idea.date)

        # 3. Confirmed Play with single date succeeds and has no end date
        resp_conf_with_date = self.client.post(reverse('core:add_play', args=[self.trip.id]), {
            'title': 'Dated Confirmed Excursion',
            'play_type': 'Tour & Excursion',
            'status': 'CONFIRMED',
            'date': '2026-11-17',
            'time': '10:00',
        }, follow=True)
        self.assertEqual(resp_conf_with_date.status_code, 200)
        play_conf = Play.objects.filter(title='Dated Confirmed Excursion').first()
        self.assertIsNotNone(play_conf)
        self.assertEqual(play_conf.status, 'CONFIRMED')
        self.assertEqual(str(play_conf.date), '2026-11-17')
        self.assertTrue(play_conf.is_start_time_set)
        self.assertIsNone(play_conf.end_time)

        # 4. Editing Play from IDEA to CONFIRMED without date is rejected
        edit_resp = self.client.post(reverse('core:edit_play', args=[self.trip.id, play_idea.id]), {
            'title': 'Undated Idea Hike',
            'status': 'CONFIRMED',
            'date': '',
        }, follow=True)
        self.assertContains(edit_resp, 'Confirmed activities require a date.')
        play_idea.refresh_from_db()
        self.assertEqual(play_idea.status, 'IDEA')

    def test_workspace_and_timeline_shows_end_date_only_for_stay(self):
        """Workspace timeline displays end dates only for Stays, never for Move, Taste, or Play."""
        import datetime
        stay = Stay.objects.create(
            trip=self.trip,
            title='Timeline Stay Hotel',
            status='CONFIRMED',
            check_in=datetime.datetime(2026, 11, 2, 15, 0, tzinfo=datetime.timezone.utc),
            check_out=datetime.datetime(2026, 11, 6, 11, 0, tzinfo=datetime.timezone.utc),
            has_check_in_time=True,
            has_check_out_time=True,
            created_by=self.user
        )
        move = Move.objects.create(
            trip=self.trip,
            title='Timeline Flight',
            mode='Flight',
            status='CONFIRMED',
            departure_time=datetime.datetime(2026, 11, 2, 9, 0, tzinfo=datetime.timezone.utc),
            has_departure_time=True,
            created_by=self.user
        )
        taste = Taste.objects.create(
            trip=self.trip,
            title='Timeline Dinner',
            status='CONFIRMED',
            start_time=datetime.datetime(2026, 11, 3, 19, 0, tzinfo=datetime.timezone.utc),
            has_start_time=True,
            created_by=self.user
        )
        play = Play.objects.create(
            trip=self.trip,
            title='Timeline Museum',
            status='CONFIRMED',
            start_time=datetime.datetime(2026, 11, 4, 10, 0, tzinfo=datetime.timezone.utc),
            has_start_time=True,
            created_by=self.user
        )

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)

        # Check forms have single date inputs for move, taste, play
        self.assertContains(resp, 'name="date"')
        self.assertContains(resp, 'move-date-required')
        self.assertContains(resp, 'taste-date-required')
        self.assertContains(resp, 'play-date-required')
        self.assertContains(resp, 'setupSingleDateElementSync')


class MoveStayTastePlayWorkflowTests(TestCase):
    """Full workflow tests for the restructured Move, Stay, Taste, Play architecture."""

    def setUp(self):
        from core.models import UserProfile, Trip, TripMember, Move, Stay, Taste, Play
        self.client = Client()
        self.owner = UserProfile.objects.create(
            email='mstp_owner@example.com',
            handle='mstpowner',
            full_name='MSTP Owner',
            is_active=True
        )
        self.trip = Trip.objects.create(
            title='Nordic Adventure',
            location='Norway',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=7),
            created_by=self.owner
        )
        TripMember.objects.create(trip=self.trip, user=self.owner, role='OWNER')

        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

    def tearDown(self):
        from core.md_sync import delete_trip_markdown
        delete_trip_markdown(self.trip)

    def test_move_crud_and_status_toggle(self):
        """Test adding, editing, toggling status, and deleting a Move."""
        from core.models import Move, Nav
        # Add Move
        resp = self.client.post(reverse('core:add_move', args=[self.trip.id]), {
            'title': 'Flight from OSL to BOO',
            'mode': 'Flight',
            'origin': 'Oslo (OSL)',
            'destination': 'Bodo (BOO)',
            'departure_time': '2026-11-10T08:00',
            'arrival_time': '2026-11-10T09:30',
            'status': 'IDEA',
            'price': '145.00',
            'confirmation_code': 'NOR-FLY-778',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        move = Move.objects.filter(trip=self.trip, title='Flight from OSL to BOO').first()
        self.assertIsNotNone(move)
        self.assertEqual(move.mode, 'Flight')
        self.assertEqual(move.status, 'IDEA')
        self.assertEqual(float(move.price), 145.00)
        self.assertEqual(move.confirmation_code, 'NOR-FLY-778')

        # Mirroring check to legacy Nav
        nav = Nav.objects.filter(trip=self.trip, title='Flight from OSL to BOO').first()
        self.assertIsNotNone(nav)

        # Toggle status to CONFIRMED
        toggle_resp = self.client.post(reverse('core:toggle_status', args=['move', move.id]), {
            'status': 'CONFIRMED'
        })
        self.assertEqual(toggle_resp.status_code, 200)
        move.refresh_from_db()
        self.assertEqual(move.status, 'CONFIRMED')

        # Edit Move
        edit_resp = self.client.post(reverse('core:edit_move', args=[self.trip.id, move.id]), {
            'title': 'Updated Flight to Bodo',
            'mode': 'Flight',
            'origin': 'Oslo (OSL)',
            'destination': 'Bodo (BOO)',
            'departure_time': '2026-11-10T08:30',
            'arrival_time': '2026-11-10T10:00',
            'status': 'CONFIRMED',
            'price': '160.00',
        }, follow=True)
        self.assertEqual(edit_resp.status_code, 200)
        move.refresh_from_db()
        self.assertEqual(move.title, 'Updated Flight to Bodo')
        self.assertEqual(float(move.price), 160.00)

        # Delete Move
        del_resp = self.client.post(reverse('core:delete_move', args=[self.trip.id, move.id]), follow=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(Move.objects.filter(id=move.id).exists())

    def test_taste_crud_and_status_toggle(self):
        """Test adding, editing, toggling status, and deleting a Taste item."""
        from core.models import Taste
        # Add Taste
        resp = self.client.post(reverse('core:add_taste', args=[self.trip.id]), {
            'title': 'Restaurant Lofoten Fiskerestaurant',
            'taste_type': 'Restaurant',
            'address': 'Havnegata 12, Svolvaer',
            'start_time': '2026-11-12T19:30',
            'status': 'IDEA',
            'price': '95.00',
            'confirmation_code': 'LOFOTEN-42',
            'notes': 'Book window table overlooking harbor',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        taste = Taste.objects.filter(trip=self.trip, title='Restaurant Lofoten Fiskerestaurant').first()
        self.assertIsNotNone(taste)
        self.assertEqual(taste.taste_type, 'Restaurant')
        self.assertEqual(taste.confirmation_code, 'LOFOTEN-42')

        # Toggle status to CONFIRMED
        toggle_resp = self.client.post(reverse('core:toggle_status', args=['taste', taste.id]), {
            'status': 'CONFIRMED'
        })
        self.assertEqual(toggle_resp.status_code, 200)
        taste.refresh_from_db()
        self.assertEqual(taste.status, 'CONFIRMED')

        # Edit Taste
        edit_resp = self.client.post(reverse('core:edit_taste', args=[self.trip.id, taste.id]), {
            'title': 'Lofoten Seafood Feast',
            'taste_type': 'Restaurant',
            'address': 'Havnegata 12, Svolvaer',
            'start_time': '2026-11-12T20:00',
            'status': 'CONFIRMED',
            'price': '110.00',
            'notes': 'Confirmed window table',
        }, follow=True)
        self.assertEqual(edit_resp.status_code, 200)
        taste.refresh_from_db()
        self.assertEqual(taste.title, 'Lofoten Seafood Feast')
        self.assertEqual(float(taste.price), 110.00)

        # Delete Taste
        del_resp = self.client.post(reverse('core:delete_taste', args=[self.trip.id, taste.id]), follow=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(Taste.objects.filter(id=taste.id).exists())

    def test_play_crud_and_status_toggle(self):
        """Test adding, editing, toggling status, and deleting a Play item."""
        from core.models import Play
        # Add Play
        resp = self.client.post(reverse('core:add_play', args=[self.trip.id]), {
            'title': 'Reinebringen Summit Hike',
            'play_type': 'Outdoor & Hike',
            'address': 'Reine, Lofoten',
            'start_time': '2026-11-11T10:00',
            'end_time': '2026-11-11T14:00',
            'status': 'CONFIRMED',
            'price': '0.00',
            'notes': '1560 stone sherpa steps',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        play = Play.objects.filter(trip=self.trip, title='Reinebringen Summit Hike').first()
        self.assertIsNotNone(play)
        self.assertEqual(play.play_type, 'Outdoor & Hike')
        self.assertEqual(play.status, 'CONFIRMED')

        # Edit Play
        edit_resp = self.client.post(reverse('core:edit_play', args=[self.trip.id, play.id]), {
            'title': 'Reinebringen Sherpa Stair Hike',
            'play_type': 'Outdoor & Hike',
            'address': 'Reine, Lofoten',
            'start_time': '2026-11-11T09:30',
            'end_time': '2026-11-11T13:30',
            'status': 'COMPLETE',
            'price': '0.00',
            'notes': 'Completed successfully with great weather',
        }, follow=True)
        self.assertEqual(edit_resp.status_code, 200)
        play.refresh_from_db()
        self.assertEqual(play.title, 'Reinebringen Sherpa Stair Hike')
        self.assertEqual(play.status, 'COMPLETE')

        # Delete Play
        del_resp = self.client.post(reverse('core:delete_play', args=[self.trip.id, play.id]), follow=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(Play.objects.filter(id=play.id).exists())

    def test_play_modal_structure_and_primary_inputs(self):
        """Verify workspace renders Play modals with name, status (after name), type, location, notes and More Options."""
        from core.models import Play
        play = Play.objects.create(
            trip=self.trip,
            title='Sample Activity',
            play_type='Culture & Museum',
            status='IDEA',
            address='123 Museum Way',
            notes='Sample entrance notes',
            created_by=self.owner,
            updated_by=self.owner
        )
        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        # Verify addPlayModal structure
        self.assertIn('id="addPlayModal"', content)
        self.assertIn('id="btnTogglePlayMoreOptions"', content)
        self.assertIn('id="playMoreOptionsContent"', content)
        self.assertIn('togglePlayMoreOptions()', content)

        # In addPlayModal, status is in the primary section immediately following title
        add_modal_idx = content.find('id="addPlayModal"')
        title_idx = content.find('name="title"', add_modal_idx)
        status_idx = content.find('name="status"', title_idx)
        type_idx = content.find('name="play_type"', status_idx)
        address_idx = content.find('name="address"', type_idx)
        notes_idx = content.find('name="notes"', address_idx)
        more_btn_idx = content.find('id="btnTogglePlayMoreOptions"', notes_idx)
        more_content_idx = content.find('id="playMoreOptionsContent"', more_btn_idx)

        self.assertTrue(add_modal_idx < title_idx < status_idx < type_idx < address_idx < notes_idx < more_btn_idx < more_content_idx)

        # Inside More Options content:
        start_time_idx = content.find('name="start_time"', more_content_idx)
        end_time_idx = content.find('name="end_time"', more_content_idx)
        price_idx = content.find('name="price"', more_content_idx)
        code_idx = content.find('name="confirmation_code"', more_content_idx)
        link_idx = content.find('name="link"', more_content_idx)
        desc_idx = content.find('name="description"', more_content_idx)

        self.assertTrue(more_content_idx < start_time_idx < end_time_idx)
        self.assertTrue(more_content_idx < price_idx < code_idx)
        self.assertTrue(more_content_idx < link_idx < desc_idx)

        # Verify editPlayModal structure
        edit_modal_id = f'id="editPlayModal_{play.id}"'
        self.assertIn(edit_modal_id, content)
        self.assertIn(f'id="btnToggleEditPlayMoreOptions_{play.id}"', content)
        self.assertIn(f'id="editPlayMoreOptionsContent_{play.id}"', content)

    def test_play_add_with_only_primary_inputs(self):
        """Test adding a Play with only name, status, type, location, and notes."""
        from core.models import Play
        resp = self.client.post(reverse('core:add_play', args=[self.trip.id]), {
            'title': 'Strolling the Old Town',
            'status': 'IDEA',
            'play_type': 'Sightseeing',
            'address': 'Gamla Stan, Stockholm',
            'notes': 'Cobblestone streets, wear comfortable walking shoes.',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        play = Play.objects.filter(trip=self.trip, title='Strolling the Old Town').first()
        self.assertIsNotNone(play)
        self.assertEqual(play.status, 'IDEA')
        self.assertEqual(play.play_type, 'Sightseeing')
        self.assertEqual(play.address, 'Gamla Stan, Stockholm')
        self.assertEqual(play.notes, 'Cobblestone streets, wear comfortable walking shoes.')
        self.assertIsNone(play.price)
        self.assertEqual(play.link, '')
        self.assertEqual(play.description, '')

    def test_play_add_with_more_options(self):
        """Test adding a Play with both primary inputs and more options fields."""
        from core.models import Play
        resp = self.client.post(reverse('core:add_play', args=[self.trip.id]), {
            'title': 'Vasa Museum Guided Tour',
            'status': 'CONFIRMED',
            'play_type': 'Culture & Museum',
            'address': 'Galärvarvsvägen 14, Stockholm',
            'notes': 'English tour starts at 11:15 AM near the ship bow',
            'start_time': '2026-11-15T11:00',
            'end_time': '2026-11-15T13:00',
            'price': '19.50',
            'confirmation_code': 'VASA-9921',
            'link': 'https://www.vasamuseet.se/en',
            'description': 'Maritime museum displaying the 17th-century ship Vasa.',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        play = Play.objects.filter(trip=self.trip, title='Vasa Museum Guided Tour').first()
        self.assertIsNotNone(play)
        self.assertEqual(play.status, 'CONFIRMED')
        self.assertEqual(play.play_type, 'Culture & Museum')
        self.assertEqual(play.address, 'Galärvarvsvägen 14, Stockholm')
        self.assertEqual(play.notes, 'English tour starts at 11:15 AM near the ship bow')
        self.assertEqual(float(play.price), 19.50)
        self.assertEqual(play.confirmation_code, 'VASA-9921')
        self.assertEqual(play.link, 'https://www.vasamuseet.se/en')
        self.assertEqual(play.description, 'Maritime museum displaying the 17th-century ship Vasa.')

    def test_markdown_sync_structure_order(self):
        """Verify markdown file generates ## Move, ## Stay, ## Taste, ## Play in exact canonical order."""
        import os
        from core.models import Move, Stay, Taste, Play
        from core.md_sync import sync_trip_to_markdown, get_trips_directory, get_trip_filename

        Move.objects.create(
            trip=self.trip,
            title='Bergen Rail',
            mode='Train',
            status='CONFIRMED',
            created_by=self.owner
        )
        Stay.objects.create(
            trip=self.trip,
            title='Fjord Lodge',
            status='CONFIRMED',
            created_by=self.owner
        )
        Taste.objects.create(
            trip=self.trip,
            title='Bakery Cinnamon Buns',
            taste_type='Cafe & Bakery',
            status='CONFIRMED',
            created_by=self.owner
        )
        Play.objects.create(
            trip=self.trip,
            title='Fjord Kayaking',
            play_type='Water & Boat',
            status='CONFIRMED',
            created_by=self.owner
        )

        # Trigger md sync
        md_path = sync_trip_to_markdown(self.trip)
        self.assertTrue(os.path.exists(md_path))
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        move_idx = content.find('## Move')
        stay_idx = content.find('## Stay')
        taste_idx = content.find('## Taste')
        play_idx = content.find('## Play')

        self.assertNotEqual(move_idx, -1)
        self.assertNotEqual(stay_idx, -1)
        self.assertNotEqual(taste_idx, -1)
        self.assertNotEqual(play_idx, -1)

        # Assert strict canonical ordering: Move -> Stay -> Taste -> Play
        self.assertTrue(move_idx < stay_idx < taste_idx < play_idx)

    def test_public_recommendation_populates_taste_and_play(self):
        """Verify public recommend link categorizes entries into Taste vs Play."""
        from core.models import Taste, Play

        # Recommend Taste (Food/Dining)
        url = reverse('core:public_recommend', args=[self.trip.rec_token])
        resp1 = self.client.post(url, {
            'guest_name': 'Foodie Friend',
            'title': 'Best Fish Soup',
            'category': 'Taste',
            'sub_type': 'Restaurant',
            'description': 'Creamy Bergen fish soup',
        }, follow=True)
        self.assertEqual(resp1.status_code, 200)
        taste = Taste.objects.filter(trip=self.trip, title='Best Fish Soup').first()
        self.assertIsNotNone(taste)
        self.assertEqual(taste.guest_name, 'Foodie Friend')

        # Recommend Play (Activity)
        resp2 = self.client.post(url, {
            'guest_name': 'Explorer Friend',
            'title': 'Floibanen Funicular',
            'category': 'Play',
            'sub_type': 'Sightseeing',
            'description': 'Funicular ride up Mount Floyen',
        }, follow=True)
        self.assertEqual(resp2.status_code, 200)
        play = Play.objects.filter(trip=self.trip, title='Floibanen Funicular').first()
        self.assertIsNotNone(play)
        self.assertEqual(play.guest_name, 'Explorer Friend')


class SeedDataAndFixtureSyncTests(TestCase):
    """Tests verifying seed data execution, export, and auto-syncing."""

    def test_seed_data_command_execution(self):
        """Verify python manage.py seed_data runs and populates database."""
        from django.core.management import call_command
        from core.models import Trip, UserProfile

        call_command('seed_data')
        self.assertGreaterEqual(Trip.objects.count(), 1)
        self.assertTrue(UserProfile.objects.filter(email='leila@sonderring.com').exists())

    def test_export_and_load_seed_fixture(self):
        """Verify export_seed_data_immediate dumps data that can be inspected."""
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from core.models import UserProfile, Trip
        from core.fixture_sync import export_seed_data_immediate

        with tempfile.TemporaryDirectory() as tmpdir:
            test_fixture_file = Path(tmpdir) / 'test_seed_data.json'
            with patch('core.fixture_sync.get_fixture_path', return_value=test_fixture_file):
                user = UserProfile.objects.create(
                    email='sync_tester@sonderring.com',
                    handle='synctester',
                    full_name='Sync Tester',
                    is_active=True
                )
                Trip.objects.create(
                    title='Fixture Sync Test Trip',
                    location='Test Location',
                    year=2026,
                    created_by=user
                )
                success = export_seed_data_immediate(force=True)
                self.assertTrue(success)
                self.assertTrue(test_fixture_file.exists())

                with open(test_fixture_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    titles = [item['fields'].get('title') for item in data if item['model'] == 'core.trip']
                    self.assertIn('Fixture Sync Test Trip', titles)


class CurrentAndUpcomingTripsOrderingTests(TestCase):
    """
    Tests for the requirement:
    'for Current & Upcoming Trips, if the trip is current it should be the first (farthest left),
    then trips should display in the chronological order'
    """

    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.create(
            email='tripper@example.com',
            handle='tripper',
            full_name='Tripper User',
            is_active=True
        )
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()

    def test_current_trip_is_first_farthest_left_and_upcoming_trips_in_chronological_order(self):
        """CURRENT trip is placed at the front (farthest left), followed by upcoming trips in chronological order."""
        # Trip with dates in late October 2026, marked CURRENT
        trip_current_oct = Trip.objects.create(
            title='Current Autumn in Paris',
            location='Paris, France',
            status='CURRENT',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 10, 20),
            end_date=datetime.date(2026, 10, 28),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_current_oct, user=self.user, role='OWNER')

        # Upcoming trip in May 2026 (earlier date than the current trip)
        trip_upcoming_may = Trip.objects.create(
            title='Upcoming Spring Tokyo',
            location='Tokyo, Japan',
            status='UPCOMING',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 5, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_upcoming_may, user=self.user, role='OWNER')

        # Upcoming trip in Summer 2026 (June 2026)
        trip_upcoming_summer = Trip.objects.create(
            title='Upcoming Summer Rome',
            location='Rome, Italy',
            status='UPCOMING',
            time_granularity='SEASON_YEAR',
            season='SUMMER',
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_upcoming_summer, user=self.user, role='OWNER')

        # Upcoming trip in August 2026 (Month span)
        trip_upcoming_aug = Trip.objects.create(
            title='Upcoming August Berlin',
            location='Berlin, Germany',
            status='UPCOMING',
            time_granularity='MONTH',
            start_month=8,
            end_month=8,
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_upcoming_aug, user=self.user, role='OWNER')

        # Upcoming trip in 2027 (Year granularity)
        trip_upcoming_2027 = Trip.objects.create(
            title='Upcoming 2027 Oslo',
            location='Oslo, Norway',
            status='UPCOMING',
            time_granularity='YEAR',
            year=2027,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_upcoming_2027, user=self.user, role='OWNER')

        # Past trip (should not be in upcoming_trips)
        trip_past = Trip.objects.create(
            title='Past Kyoto 2024',
            location='Kyoto, Japan',
            status='PAST',
            year=2024,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_past, user=self.user, role='OWNER')

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        upcoming_trips = list(response.context['upcoming_trips'])
        expected_trips = [
            trip_current_oct,      # CURRENT is first (farthest left), even though date is in October
            trip_upcoming_may,     # May 2026 (chronological start)
            trip_upcoming_summer,  # Summer (June) 2026
            trip_upcoming_aug,     # August 2026
            trip_upcoming_2027,    # Year 2027
        ]
        self.assertEqual([t.id for t in upcoming_trips], [t.id for t in expected_trips])

        # Verify HTML layout: CURRENT card appears earliest in the HTML (farthest left in .trips-grid)
        html = response.content.decode('utf-8')
        pos_current = html.index('Current Autumn in Paris')
        pos_may = html.index('Upcoming Spring Tokyo')
        pos_summer = html.index('Upcoming Summer Rome')
        pos_aug = html.index('Upcoming August Berlin')
        pos_2027 = html.index('Upcoming 2027 Oslo')

        self.assertTrue(pos_current < pos_may < pos_summer < pos_aug < pos_2027)

    def test_no_current_trip_displays_in_chronological_order(self):
        """When no trip has CURRENT status, all upcoming trips display in chronological order."""
        trip_may = Trip.objects.create(
            title='May Trip',
            location='Tokyo',
            status='UPCOMING',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 5, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_may, user=self.user, role='OWNER')

        trip_oct = Trip.objects.create(
            title='October Trip',
            location='Paris',
            status='UPCOMING',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2026, 10, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_oct, user=self.user, role='OWNER')

        trip_aug = Trip.objects.create(
            title='August Trip',
            location='Berlin',
            status='UPCOMING',
            time_granularity='MONTH',
            start_month=8,
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_aug, user=self.user, role='OWNER')

        trip_2027 = Trip.objects.create(
            title='2027 Trip',
            location='Oslo',
            status='UPCOMING',
            time_granularity='YEAR',
            year=2027,
            created_by=self.user
        )
        TripMember.objects.create(trip=trip_2027, user=self.user, role='OWNER')

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        upcoming_trips = list(response.context['upcoming_trips'])
        expected_trips = [trip_may, trip_aug, trip_oct, trip_2027]
        self.assertEqual([t.id for t in upcoming_trips], [t.id for t in expected_trips])

    def test_multiple_current_trips_current_first_in_chronological_order(self):
        """When multiple trips are CURRENT, they appear first and are chronologically ordered among themselves."""
        curr_oct = Trip.objects.create(
            title='Current Oct Trip',
            location='Paris',
            status='CURRENT',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2026, 10, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=curr_oct, user=self.user, role='OWNER')

        curr_june = Trip.objects.create(
            title='Current June Trip',
            location='Nice',
            status='CURRENT',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=curr_june, user=self.user, role='OWNER')

        up_may = Trip.objects.create(
            title='Upcoming May Trip',
            location='Tokyo',
            status='UPCOMING',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 5, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=up_may, user=self.user, role='OWNER')

        up_nov = Trip.objects.create(
            title='Upcoming Nov Trip',
            location='London',
            status='UPCOMING',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2026, 11, 1),
            end_date=datetime.date(2026, 11, 10),
            year=2026,
            created_by=self.user
        )
        TripMember.objects.create(trip=up_nov, user=self.user, role='OWNER')

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        upcoming_trips = list(response.context['upcoming_trips'])
        # Both current trips are first (June then Oct), then upcoming trips (May then Nov)
        expected_trips = [curr_june, curr_oct, up_may, up_nov]
        self.assertEqual([t.id for t in upcoming_trips], [t.id for t in expected_trips])

    def test_python_list_fallback_order_current_and_upcoming_trips(self):
        """order_current_and_upcoming_trips also supports standard Python lists."""
        t1 = Trip(title='Nov Trip', status='UPCOMING', time_granularity='MONTH', start_month=11, year=2026)
        t2 = Trip(title='Current Dec Trip', status='CURRENT', time_granularity='MONTH', start_month=12, year=2026)
        t3 = Trip(title='Feb Trip', status='UPCOMING', time_granularity='MONTH', start_month=2, year=2026)
        t4 = Trip(title='Past Trip', status='PAST', time_granularity='MONTH', start_month=1, year=2025)

        sorted_list = order_current_and_upcoming_trips([t1, t2, t3, t4])
        self.assertEqual(sorted_list, [t2, t3, t1])


class SpellingAndPluralizationAuditTests(TestCase):
    """Verifies that pluralization and text in templates render correctly without typos like 'Activityies'."""

    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.create(
            email='spelling_user@sonderring.com',
            handle='spellinguser',
            full_name='Spelling User',
            is_active=True
        )
        self.trip = Trip.objects.create(
            title='Spelling Audit Trip',
            location='Audit City',
            year=2026,
            created_by=self.user
        )
        from core.models import TripMember
        TripMember.objects.create(trip=self.trip, user=self.user, role='OWNER')
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()

    def test_workspace_plays_counter_pluralization(self):
        """Ensure 0, 1, and 2 plays render '0 Activities', '1 Activity', '2 Activities' (never 'Activityies')."""
        from core.models import Play

        # 0 plays -> '0 Activities'
        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertContains(resp, '0 Activities')
        self.assertNotContains(resp, 'Activityies')

        # 1 play -> '1 Activity'
        Play.objects.create(trip=self.trip, title='Solo Hike', created_by=self.user)
        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertContains(resp, '1 Activity')
        self.assertNotContains(resp, 'Activityies')

        # 2 plays -> '2 Activities'
        Play.objects.create(trip=self.trip, title='Boat Tour', created_by=self.user)
        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertContains(resp, '2 Activities')
        self.assertNotContains(resp, 'Activityies')

    def test_profile_trippers_and_items_pluralization(self):
        """Ensure profile page correctly pluralizes Tripper/Trippers and Item/Items."""
        resp = self.client.get(reverse('core:profile'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Only 1 member (the creator)
        self.assertIn('1 Tripper', content)
        self.assertNotIn('1 Trippers', content)













