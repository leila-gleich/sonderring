"""
Fixture and Seed Data Synchronizer for Sonderring.
Ensures that any creation, edit, status toggle, or deletion performed on the website
automatically updates the version-controlled seed data fixture (core/fixtures/seed_data.json).
When cloned or run on another computer, `python manage.py seed_data` restores the updated database.
"""

import io
import os
import sys
import threading
from pathlib import Path
from django.conf import settings
from django.core.management import call_command

_export_timer = None
_timer_lock = threading.Lock()
_is_exporting = False
_is_loading = False


def get_fixture_path() -> Path:
    fixture_dir = Path(settings.BASE_DIR) / 'core' / 'fixtures'
    fixture_dir.mkdir(parents=True, exist_ok=True)
    return fixture_dir / 'seed_data.json'


def is_sync_disabled() -> bool:
    """Check if automatic seed export should be skipped (e.g. during tests or loading)."""
    global _is_exporting, _is_loading
    if _is_exporting or _is_loading:
        return True
    # Disable during testing or manage.py commands that shouldn't auto-export
    disallowed_cmds = {'test', 'loaddata', 'dumpdata', 'makemigrations', 'migrate', 'collectstatic'}
    if any(arg in disallowed_cmds for arg in sys.argv):
        return True
    return False


def _do_export_seed_data(force: bool = False):
    """Performs atomic export of core models to seed_data.json."""
    global _is_exporting
    if not force and is_sync_disabled():
        return False

    _is_exporting = True
    try:
        fixture_file = get_fixture_path()
        tmp_file = fixture_file.with_suffix('.json.tmp')

        buf = io.StringIO()
        call_command(
            'dumpdata',
            'core',
            indent=2,
            natural_foreign=True,
            natural_primary=True,
            stdout=buf
        )
        content = buf.getvalue()

        # Atomic file write to avoid corrupted JSON if interrupted
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(tmp_file, fixture_file)
        return True
    except Exception as e:
        print(f"[SeedSync] Notice: could not auto-export seed data: {e}", file=sys.stderr)
        return False
    finally:
        _is_exporting = False


def queue_seed_data_export(delay: float = 0.5):
    """
    Debounced trigger to export database state to core/fixtures/seed_data.json.
    Runs asynchronously in a background thread so web requests respond instantly.
    """
    global _export_timer
    if is_sync_disabled():
        return

    with _timer_lock:
        if _export_timer is not None:
            _export_timer.cancel()
        _export_timer = threading.Timer(delay, _do_export_seed_data)
        _export_timer.daemon = True
        _export_timer.start()


def export_seed_data_immediate(force: bool = False) -> bool:
    """Immediately and synchronously writes the live DB to core/fixtures/seed_data.json."""
    return _do_export_seed_data(force=force)


def load_seed_fixture() -> bool:
    """Loads core/fixtures/seed_data.json into the active database."""
    global _is_loading
    fixture_file = get_fixture_path()
    if not fixture_file.exists():
        return False

    _is_loading = True
    try:
        call_command('loaddata', str(fixture_file))
        return True
    finally:
        _is_loading = False
