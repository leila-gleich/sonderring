from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import Trip, UserProfile
from core.fixture_sync import export_seed_data_immediate
from core.md_sync import sync_trip_to_markdown


class Command(BaseCommand):
    help = (
        'Seeds Sonderring database with canonical trips, elements, and users '
        'from docs/seed-trips/ and synchronizes the seed data fixture.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--export',
            action='store_true',
            help='Exports the live database directly to core/fixtures/seed_data.json without importing.'
        )

    def handle(self, *args, **options):
        if options.get('export'):
            self.stdout.write("Exporting live database to core/fixtures/seed_data.json...")
            success = export_seed_data_immediate(force=True)
            if success:
                self.stdout.write(self.style.SUCCESS("Successfully exported seed_data.json!"))
            else:
                self.stderr.write(self.style.ERROR("Failed to export seed_data.json."))
            return

        self.stdout.write("Seeding Sonderring database from canonical docs/seed-trips/...")
        call_command('import_seed_trips', clear=True)

        # Ensure demo user passwords remain valid for all 4 canonical users
        for email, pwd in [
            ('leila@sonderring.com', 'Sonderring2026!'),
            ('sam@sonderring.com', 'Sonderring2026!'),
            ('alex@sonderring.com', 'Sonderring2026!'),
            ('jordan@sonderring.com', 'Sonderring2026!'),
        ]:
            user = UserProfile.objects.filter(email=email).first()
            if user:
                user.set_password(pwd)
                user.save()

        # Sync markdown files for all trips
        import sys
        if 'test' not in sys.argv:
            for trip in Trip.objects.all():
                sync_trip_to_markdown(trip)

        # Export synchronized state to core/fixtures/seed_data.json
        self.stdout.write("Exporting synchronized state to core/fixtures/seed_data.json...")
        export_seed_data_immediate(force=True)

        trip_count = Trip.objects.count()
        user_count = UserProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded database! Live database now has {trip_count} trip(s) and {user_count} canonical user(s)."
        ))
