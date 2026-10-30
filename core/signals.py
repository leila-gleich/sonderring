"""
Django Signals for Sonderring Markdown Synchronization and Dual-Model Compatibility.
Automatically keeps local markdown files in /Trips/ in permanent, instant synchronization
with any database change performed via web browser views, forms, or APIs.
Provides bidirectional sync between legacy models (Nav, Do, Rec) and modern models (Move, Taste, Play).
"""

import sys
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Trip, Stay, Move, Taste, Play, Nav, Do, Rec, TripMember, Attachment, UserProfile
from .md_sync import sync_trip_to_markdown, delete_trip_markdown
from .fixture_sync import queue_seed_data_export

_in_model_sync = False


def _should_sync_md() -> bool:
    return 'test' not in sys.argv


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


@receiver([post_save, post_delete], sender=Nav)
def on_nav_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Do)
def on_do_change(sender, instance, **kwargs):
    queue_seed_data_export()
    if not _should_sync_md():
        return
    try:
        if instance.trip_id:
            sync_trip_to_markdown(instance.trip)
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Rec)
def on_rec_change(sender, instance, **kwargs):
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


# ==========================================
# Dual-Model Bidirectional Synchronizers
# ==========================================

@receiver(post_save, sender=Nav)
def sync_nav_to_move(sender, instance, **kwargs):
    global _in_model_sync
    if _in_model_sync or kwargs.get('raw'):
        return
    _in_model_sync = True
    try:
        Move.objects.update_or_create(
            id=instance.id,
            defaults={
                'trip': instance.trip,
                'title': instance.title,
                'mode': instance.mode,
                'trip_stage': instance.trip_stage,
                'direction': instance.direction,
                'status': instance.status,
                'passenger_name': instance.passenger_name,
                'origin_address': instance.origin_address,
                'destination_address': instance.destination_address,
                'departure_time': instance.departure_time,
                'arrival_time': None,
                'date_confidence': instance.date_confidence,
                'time_confidence': instance.time_confidence,
                'flexibility_notes': instance.flexibility_notes,
                'price': instance.price,
                'currency': instance.currency,
                'booking_link': instance.booking_link,
                '_encrypted_confirmation_code': instance._encrypted_confirmation_code,
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
    except Exception:
        pass
    finally:
        _in_model_sync = False


@receiver(post_save, sender=Move)
def sync_move_to_nav(sender, instance, **kwargs):
    global _in_model_sync
    if _in_model_sync or kwargs.get('raw'):
        return
    _in_model_sync = True
    try:
        Nav.objects.update_or_create(
            id=instance.id,
            defaults={
                'trip': instance.trip,
                'title': instance.title,
                'mode': instance.mode,
                'trip_stage': instance.trip_stage,
                'direction': instance.direction,
                'status': instance.status,
                'passenger_name': instance.passenger_name,
                'origin_address': instance.origin_address,
                'destination_address': instance.destination_address,
                'departure_time': instance.departure_time,
                'arrival_time': None,
                'date_confidence': instance.date_confidence,
                'time_confidence': instance.time_confidence,
                'flexibility_notes': instance.flexibility_notes,
                'price': instance.price,
                'currency': instance.currency,
                'booking_link': instance.booking_link,
                '_encrypted_confirmation_code': instance._encrypted_confirmation_code,
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
    except Exception:
        pass
    finally:
        _in_model_sync = False


@receiver(post_save, sender=Do)
def sync_do_to_play_or_taste(sender, instance, **kwargs):
    global _in_model_sync
    if _in_model_sync or kwargs.get('raw'):
        return
    _in_model_sync = True
    try:
        is_dining = instance.activity_type == 'Dining' or any(
            w in instance.title.lower() for w in ['dinner', 'lunch', 'breakfast', 'restaurant', 'cafe', 'bar', 'tasting', 'wine', 'food']
        )
        if is_dining:
            Taste.objects.update_or_create(
                id=instance.id,
                defaults={
                    'trip': instance.trip,
                    'title': instance.title,
                    'taste_type': 'Restaurant',
                    'status': instance.status,
                    'address': instance.address,
                    'start_time': instance.start_time,
                    'end_time': None,
                    'has_start_time': bool(instance.start_time),
                    'has_end_time': False,
                    'price': instance.price,
                    'currency': instance.currency,
                    'link': instance.link,
                    'description': instance.description,
                    '_encrypted_confirmation_code': instance._encrypted_confirmation_code,
                    'created_by': instance.created_by,
                    'updated_by': instance.updated_by,
                }
            )
        else:
            Play.objects.update_or_create(
                id=instance.id,
                defaults={
                    'trip': instance.trip,
                    'title': instance.title,
                    'play_type': instance.activity_type if instance.activity_type in dict(Play.PLAY_TYPE_CHOICES) else 'Sightseeing',
                    'status': instance.status,
                    'address': instance.address,
                    'start_time': instance.start_time,
                    'end_time': None,
                    'has_start_time': bool(instance.start_time),
                    'has_end_time': False,
                    'price': instance.price,
                    'currency': instance.currency,
                    'link': instance.link,
                    'description': instance.description,
                    '_encrypted_confirmation_code': instance._encrypted_confirmation_code,
                    'created_by': instance.created_by,
                    'updated_by': instance.updated_by,
                }
            )
    except Exception:
        pass
    finally:
        _in_model_sync = False


@receiver(post_save, sender=Play)
def sync_play_to_do(sender, instance, **kwargs):
    global _in_model_sync
    if _in_model_sync or kwargs.get('raw'):
        return
    _in_model_sync = True
    try:
        Do.objects.update_or_create(
            id=instance.id,
            defaults={
                'trip': instance.trip,
                'title': instance.title,
                'activity_type': instance.play_type,
                'status': instance.status,
                'address': instance.address,
                'start_time': instance.start_time,
                'end_time': instance.end_time,
                'price': instance.price,
                'currency': instance.currency,
                'link': instance.link,
                'description': instance.description,
                '_encrypted_confirmation_code': instance._encrypted_confirmation_code,
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
    except Exception:
        pass
    finally:
        _in_model_sync = False


@receiver(post_save, sender=Taste)
def sync_taste_to_rec_and_do(sender, instance, **kwargs):
    global _in_model_sync
    if _in_model_sync or kwargs.get('raw'):
        return
    _in_model_sync = True
    try:
        Rec.objects.update_or_create(
            id=instance.id,
            defaults={
                'trip': instance.trip,
                'title': instance.title,
                'category': 'Food',
                'status': instance.status,
                'address': instance.address,
                'link': instance.link,
                'description': instance.description,
                'guest_name': instance.guest_name,
                'recommended_by': instance.recommended_by or instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
        Do.objects.update_or_create(
            id=instance.id,
            defaults={
                'trip': instance.trip,
                'title': instance.title,
                'activity_type': 'Dining',
                'status': instance.status,
                'address': instance.address,
                'start_time': instance.start_time,
                'end_time': instance.end_time,
                'price': instance.price,
                'currency': instance.currency,
                'link': instance.link,
                'description': instance.description,
                '_encrypted_confirmation_code': instance._encrypted_confirmation_code,
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
    except Exception:
        pass
    finally:
        _in_model_sync = False


@receiver(post_save, sender=Rec)
def sync_rec_to_taste_or_play(sender, instance, **kwargs):
    global _in_model_sync
    if _in_model_sync or kwargs.get('raw'):
        return
    _in_model_sync = True
    try:
        if instance.category == 'Food':
            Taste.objects.update_or_create(
                id=instance.id,
                defaults={
                    'trip': instance.trip,
                    'title': instance.title,
                    'taste_type': 'Restaurant',
                    'status': instance.status,
                    'address': instance.address,
                    'link': instance.link,
                    'description': instance.description,
                    'guest_name': instance.guest_name,
                    'recommended_by': instance.recommended_by,
                    'updated_by': instance.updated_by,
                }
            )
        else:
            cat_map = {'Spot': 'Sightseeing', 'Activity': 'Tour & Excursion', 'Tip': 'Travel Tip'}
            Play.objects.update_or_create(
                id=instance.id,
                defaults={
                    'trip': instance.trip,
                    'title': instance.title,
                    'play_type': cat_map.get(instance.category, 'Sightseeing'),
                    'status': instance.status,
                    'address': instance.address,
                    'link': instance.link,
                    'description': instance.description,
                    'guest_name': instance.guest_name,
                    'recommended_by': instance.recommended_by,
                    'updated_by': instance.updated_by,
                }
            )
    except Exception:
        pass
    finally:
        _in_model_sync = False


@receiver(post_delete, sender=Move)
def delete_nav_on_move_delete(sender, instance, **kwargs):
    Nav.objects.filter(id=instance.id).delete()


@receiver(post_delete, sender=Nav)
def delete_move_on_nav_delete(sender, instance, **kwargs):
    Move.objects.filter(id=instance.id).delete()


@receiver(post_delete, sender=Taste)
def delete_rec_on_taste_delete(sender, instance, **kwargs):
    Rec.objects.filter(id=instance.id).delete()
    Do.objects.filter(id=instance.id).delete()


@receiver(post_delete, sender=Play)
def delete_do_on_play_delete(sender, instance, **kwargs):
    Do.objects.filter(id=instance.id).delete()
