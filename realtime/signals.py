"""
Django signals that push real-time notifications via Channels.
"""

import logging
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

logger = logging.getLogger('realtime')


def _send_to_user(user_id: int, event: str, data: dict):
    """
    Utility: push a notification to a single user's WebSocket group.

    Runs synchronously – safe to call from signal handlers.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            f'user_{user_id}',
            {
                'type': 'notification',
                'event': event,
                'data': data,
            },
        )
    except Exception as exc:
        logger.debug('Failed to push WS event: %s', exc)


@receiver(post_save, sender='music.Track')
def notify_new_track(sender, instance, created, **kwargs):
    """
    When a new track is created, notify users who follow that artist.
    (Simplified: in production you'd query a 'follows' table.)
    """
    if not created:
        return

    data = {
        'track_id': instance.id,
        'title': instance.title,
        'artist': instance.artist.name,
        'message': f'New release: {instance.title} by {instance.artist.name}',
    }

    # In a full implementation you'd query UserFollow or similar.
    # Here we demonstrate the pattern by notifying the admin user (id=1).
    _send_to_user(1, 'track_released', data)


@receiver(post_save, sender='streaming.PlayHistory')
def broadcast_now_playing(sender, instance, created, **kwargs):
    """
    When a play-history entry is created, broadcast a now-playing event.
    """
    if not created:
        return

    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            'now_playing',
            {
                'type': 'now_playing',
                'data': {
                    'user_id': instance.user_id,
                    'username': instance.user.username,
                    'track_id': instance.track_id,
                    'track_title': instance.track.title,
                },
            },
        )
    except Exception as exc:
        logger.debug('now_playing broadcast failed: %s', exc)
