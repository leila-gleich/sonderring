"""
Django Signals for Sonderring Markdown Synchronization.
Automatically keeps local markdown files in /Trips/ in permanent, instant synchronization
with any database change performed via web browser views, forms, or APIs.
"""

import sys
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Trip, Stay, Move, Taste, Play, TripMember, Attachment, UserProfile
from .md_sync import sync_trip_to_markdown, delete_trip_markdown
from .fixture_sync import queue_seed_data_export


def _should_sync_md() -> bool:
    import core.md_sync
    if getattr(core.md_sync, '_is_syncing', False):
        return False
    disallowed = {'test', 'import_seed_trips', 'seed_data', 'loaddata', 'dumpdata'}
    if any(arg in disallowed for arg in sys.argv):
        return False
    return True


@receiver(post_save, sender=Trip)
def on_trip_save(sender, instance, **kwargs):
    if _should_sync_md():
        sync_trip_to_markdown(instance)
    queue_seed_data_export()


@receiver(post_delete, sender=Trip)
def on_trip_delete(sender, instance, **kwargs):
    if _should_sync_md():
        delete_trip_markdown(instance)
    queue_seed_data_export()


# ==========================================
# Markdown & Fixture Synchronizers
# ==========================================

@receiver([post_save, post_delete], sender=UserProfile)
def on_user_change(sender, instance, **kwargs):
    queue_seed_data_export()


@receiver([post_save, post_delete], sender=Move)
def on_move_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Stay)
def on_stay_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Taste)
def on_taste_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Play)
def on_play_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=TripMember)
def on_member_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Attachment)
def on_attachment_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver(post_delete, sender=Attachment)
def on_attachment_file_cleanup(sender, instance, **kwargs):
    """Immediately purges the underlying physical file from storage upon Attachment deletion."""
    try:
        if instance.file and instance.file.name:
            instance.file.delete(save=False)
    except Exception:
        pass
