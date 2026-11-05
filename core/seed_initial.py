"""
Canonical Initial Data Bootstrapper for Sonderring.
Bootstraps the 9 authentic, verified trips from docs/seed-trips/ into the active database.
"""

from django.core.management import call_command
from core.models import Trip, UserProfile


def bootstrap_canonical_trips(stdout=None):
    def log(msg):
        if stdout and hasattr(stdout, "write"):
            stdout.write(str(msg) + "\n")
        else:
            print(msg)

    # 1. Ensure core demo users exist with valid credentials
    for handle, email, name, phone in [
        ('leila', 'leila@sonderring.com', 'Leila Gleich', '+1-310-555-0192'),
        ('samt', 'sam@sonderring.com', 'Sam Taylor', '+1-415-555-0144'),
        ('alexm', 'alex@sonderring.com', 'Alex Morgan', '+1-212-555-0188'),
        ('jordanl', 'jordan@sonderring.com', 'Jordan Lee', '+1-646-555-0163'),
    ]:
        user, _ = UserProfile.objects.get_or_create(
            email=email,
            defaults={
                'handle': handle,
                'full_name': name,
                'phone_number': phone,
            }
        )
        if not user.has_usable_password():
            user.set_password('Sonderring2026!')
            user.save()

    # Only bootstrap canonical trips if no trips exist in database;
    # NEVER delete or overwrite existing user-created trips!
    if Trip.objects.exists():
        log("Trips already exist in database. Preserving all existing user trips and skipping baseline overwrite.")
        return

    log("Bootstrapping Sonderring database with canonical seed trips...")
    call_command('import_seed_trips')
