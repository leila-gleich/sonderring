from django.core.management.base import BaseCommand
from core.models import Trip


class Command(BaseCommand):
    help = (
        '[ARCHIVED] Initial demo trip seeding has been archived to '
        'archive/seed_data_initial.py to protect live database records.'
    )

    def handle(self, *args, **options):
        trip_count = Trip.objects.count()
        self.stderr.write(self.style.ERROR(
            f"\n🔒 SAFETY BLOCK: 'seed_data' is disabled and archived.\n"
            f"Your PostgreSQL database currently holds {trip_count} live trip(s).\n"
            f"Resetting or overwriting trips from scratch is permanently disabled.\n"
            f"(Historical bootstrap script is archived at: ../archive/seed_data_initial.py)\n"
        ))
        return
