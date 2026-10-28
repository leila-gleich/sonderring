"""
Django Signals for Sonderring Markdown Synchronization.
Automatically keeps local markdown files in /Trips/ in permanent, instant synchronization
with any database change performed via web browser views, forms, or APIs.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Trip, Stay, Nav, Do, Rec, TripMember, Attachment
from .md_sync import sync_trip_to_markdown, delete_trip_markdown


@receiver(post_save, sender=Trip)
def on_trip_save(sender, instance, **kwargs):
    sync_trip_to_markdown(instance)


@receiver(post_delete, sender=Trip)
def on_trip_delete(sender, instance, **kwargs):
    delete_trip_markdown(instance)


@receiver([post_save, post_delete], sender=Stay)
def on_stay_change(sender, instance, **kwargs):
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Nav)
def on_nav_change(sender, instance, **kwargs):
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Do)
def on_do_change(sender, instance, **kwargs):
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Rec)
def on_rec_change(sender, instance, **kwargs):
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=TripMember)
def on_member_change(sender, instance, **kwargs):
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Attachment)
def on_attachment_change(sender, instance, **kwargs):
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
