"""
WebSocket consumers for real-time notifications.

Uses Django Channels to push events to connected clients:
- New track releases
- Playlist updates (tracks added/removed by collaborators)
- Now-playing status of friends
- System notifications
"""

import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

logger = logging.getLogger('realtime')


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Per-user notification channel.

    Connect:  ws://<host>/ws/notifications/?token=<jwt>
    Groups:   user_{user_id}

    Inbound messages (client → server):
        {"type": "ping"}

    Outbound messages (server → client):
        {"type": "notification", "event": "<event>", "data": {...}}
    """

    async def connect(self):
        self.user = self.scope.get('user')

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.user_group = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

        logger.info('WS connected: user=%s channel=%s', self.user.id, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        logger.info('WS disconnected: code=%s', close_code)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')

        if msg_type == 'ping':
            await self.send_json({'type': 'pong'})

    # ------------------------------------------------------------------
    # Handlers for messages sent via channel_layer.group_send
    # ------------------------------------------------------------------

    async def notification(self, event):
        """Generic notification push."""
        await self.send_json({
            'type': 'notification',
            'event': event.get('event'),
            'data': event.get('data', {}),
        })

    async def track_released(self, event):
        """New track from a followed artist."""
        await self.send_json({
            'type': 'notification',
            'event': 'track_released',
            'data': event.get('data', {}),
        })

    async def playlist_updated(self, event):
        """Collaborative playlist was updated."""
        await self.send_json({
            'type': 'notification',
            'event': 'playlist_updated',
            'data': event.get('data', {}),
        })

    async def now_playing(self, event):
        """A friend started playing a track."""
        await self.send_json({
            'type': 'notification',
            'event': 'now_playing',
            'data': event.get('data', {}),
        })


class NowPlayingConsumer(AsyncJsonWebsocketConsumer):
    """
    Broadcast now-playing status to a shared group.

    Connect:  ws://<host>/ws/now-playing/
    Groups:   now_playing (global)

    Inbound messages:
        {"type": "update", "track_id": 123}

    Outbound messages:
        {"type": "now_playing", "user": "...", "track_id": 123}
    """

    GROUP_NAME = 'now_playing'

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')

        if msg_type == 'update':
            track_id = content.get('track_id')
            await self.channel_layer.group_send(
                self.GROUP_NAME,
                {
                    'type': 'now_playing',
                    'data': {
                        'user_id': self.user.id,
                        'username': self.user.username,
                        'track_id': track_id,
                    },
                },
            )

    async def now_playing(self, event):
        await self.send_json({
            'type': 'now_playing',
            'data': event.get('data', {}),
        })
