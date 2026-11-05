from django.core.management.base import BaseCommand
from core.models import Trip, UserProfile
from core.fixture_sync import get_fixture_path, load_seed_fixture, export_seed_data_immediate
from core.seed_initial import bootstrap_canonical_trips
from core.md_sync import sync_trip_to_markdown


class Command(BaseCommand):
    help = (
        'Seeds Sonderring database with trips, elements, and users. '
        'Loads the latest auto-synced fixture (core/fixtures/seed_data.json) if available, '
        'or bootstraps from canonical initial data.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--export',
            action='store_true',
            help='Exports the live database directly to core/fixtures/seed_data.json without loading.'
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

        fixture_file = get_fixture_path()

        if fixture_file.exists():
            self.stdout.write(f"Loading user-updated seed data from {fixture_file}...")
            loaded = load_seed_fixture()
            if not loaded:
                self.stderr.write(self.style.ERROR(
                    f"Notice: Could not load fixture from {fixture_file}. "
                    "Preserving existing database and fixture to prevent data loss."
                ))
                return
        else:
            if Trip.objects.exists():
                self.stdout.write("Database contains trips. Preserving and exporting to core/fixtures/seed_data.json...")
                export_seed_data_immediate(force=True)
            else:
                self.stdout.write("No fixture file found and database is empty. Bootstrapping initial canonical trips...")
                bootstrap_canonical_trips(stdout=self.stdout)
                export_seed_data_immediate(force=True)

        # Ensure demo user passwords remain valid
        for email, pwd in [
            ('leila@sonderring.com', 'Sonderring2026!'),
            ('sam@sonderring.com', 'Sonderring2026!'),
            ('alex@sonderring.com', 'Sonderring2026!'),
            ('jordan@sonderring.com', 'Sonderring2026!'),
        ]:
            user = UserProfile.objects.filter(email=email).first()
            if user and not user.has_usable_password():
                user.set_password(pwd)
                user.save()

        # Sync markdown files for all trips
        import sys
        if 'test' not in sys.argv:
            for trip in Trip.objects.all():
                sync_trip_to_markdown(trip)

        trip_count = Trip.objects.count()
        user_count = UserProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded database! Live database now has {trip_count} trip(s) and {user_count} user(s)."
        ))
