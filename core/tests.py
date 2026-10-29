from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.template.context import BaseContext
from core.models import UserProfile, OAuthIdentity, Trip, TripMember, Stay, Nav, Do, Rec, Attachment, SecurityAuditLog

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

    def test_viewer_cannot_edit_delete_or_toggle_any_item(self):
        """Viewers are strictly read-only and cannot edit, delete, or toggle status even on items attributed to them."""
        stay_by_viewer = Stay.objects.create(
            trip=self.trip,
            title='Original Stay',
            status='IDEA',
            created_by=self.viewer
        )
        session = self.client.session
        session['user_id'] = str(self.viewer.id)
        session.save()

        # Cannot edit
        self.client.post(reverse('core:edit_stay', args=[self.trip.id, stay_by_viewer.id]), {'title': 'Tampered Stay'})
        stay_by_viewer.refresh_from_db()
        self.assertEqual(stay_by_viewer.title, 'Original Stay')

        # Cannot toggle status
        resp_toggle = self.client.post(
            reverse('core:toggle_status', args=['stay', stay_by_viewer.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp_toggle.status_code, 403)
        stay_by_viewer.refresh_from_db()
        self.assertEqual(stay_by_viewer.status, 'IDEA')

        # Cannot delete
        self.client.post(reverse('core:delete_stay', args=[self.trip.id, stay_by_viewer.id]))
        self.assertTrue(Stay.objects.filter(id=stay_by_viewer.id).exists())

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

    def test_workspace_displays_rec_invite_link_and_sndr_tabs(self):
        """Verify workspace top section contains copyable recommendation invite link and SNDR tabs."""
        session = self.client.session
        session['user_id'] = str(self.owner.id)
        session.save()

        resp = self.client.get(reverse('core:trip_workspace', args=[self.trip.id]))
        self.assertEqual(resp.status_code, 200)
        # SNDR tab elements
        self.assertContains(resp, 'title="Sonderring S Element: Stays">S</span>')
        self.assertContains(resp, 'title="Sonderring N Element: Navs">N</span>')
        self.assertContains(resp, 'title="Sonderring D Element: Dos">D</span>')
        self.assertContains(resp, 'title="Sonderring R Element: Recs">R</span>')
        # Copy link widget in top section
        self.assertContains(resp, 'rec-invite-bar')
        self.assertContains(resp, self.trip.rec_token)
        self.assertContains(resp, 'Copy Rec Link')


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
        """Top workspace detail section has 'Add Element' button & dropdown for all 4 elements (S, N, D, R)."""
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
        self.assertContains(resp, "openAddElement('stay')")
        self.assertContains(resp, "openAddElement('nav')")
        self.assertContains(resp, "openAddElement('do')")
        self.assertContains(resp, "openAddElement('rec')")

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









