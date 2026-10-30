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
            '--reset',
            action='store_true',
            help='Wipes existing Trip records before seeding.'
        )
        parser.add_argument(
            '--initial',
            action='store_true',
            help='Forces rebuilding from canonical 11 initial trips and updates seed_data.json.'
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Exports the live database directly to core/fixtures/seed_data.json without loading.'
        )

    def handle(self, *args, **options):
        if options.get('export'):
            self.stdout.write("Exporting live database to core/fixtures/seed_data.json...")
            success = export_seed_data_immediate()
            if success:
                self.stdout.write(self.style.SUCCESS("Successfully exported seed_data.json!"))
            else:
                self.stderr.write(self.style.ERROR("Failed to export seed_data.json."))
            return

        fixture_file = get_fixture_path()
        use_initial = options.get('initial') or not fixture_file.exists()

        if options.get('reset'):
            self.stdout.write("Clearing existing trips for clean re-seeding...")
            Trip.objects.all().delete()

        if use_initial:
            self.stdout.write("Bootstrapping canonical Sonderring trips and users...")
            bootstrap_canonical_trips(stdout=self.stdout)
            self.stdout.write("Exporting canonical dataset to core/fixtures/seed_data.json...")
            export_seed_data_immediate()
        else:
            self.stdout.write(f"Loading seed data from {fixture_file}...")
            loaded = load_seed_fixture()
            if not loaded:
                self.stderr.write(self.style.ERROR(f"Could not load {fixture_file}, falling back to initial data."))
                bootstrap_canonical_trips(stdout=self.stdout)
                export_seed_data_immediate()
            else:
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
                for trip in Trip.objects.all():
                    sync_trip_to_markdown(trip)

        trip_count = Trip.objects.count()
        user_count = UserProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded database! Live database now has {trip_count} trip(s) and {user_count} user(s)."
        ))
