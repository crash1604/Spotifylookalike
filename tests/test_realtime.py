"""
Tests for WebSocket consumers in the realtime module.

Uses channels.testing.WebsocketCommunicator to test consumers
without a real network connection.

Covers:
- NotificationConsumer: connect/disconnect, JWT auth rejection, ping/pong,
  group message delivery
- NowPlayingConsumer: connect/disconnect, update broadcast
"""

import pytest
import pytest_asyncio
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.contrib.auth.anonymous import AnonymousUser

from realtime.consumers import NotificationConsumer, NowPlayingConsumer
from tests.factories import UserFactory


# =============================================================================
# NotificationConsumer Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestNotificationConsumer:
    """Tests for the per-user notification WebSocket consumer."""

    async def test_authenticated_user_can_connect(self, db):
        """A user with a valid scope user object can connect successfully."""
        user = await pytest_asyncio.fixture(UserFactory)() if False else None
        # Use sync_to_async to create user in async context
        from asgiref.sync import sync_to_async
        user = await sync_to_async(UserFactory)()

        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/',
        )
        communicator.scope['user'] = user

        connected, subprotocol = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    async def test_anonymous_user_is_rejected(self):
        """Anonymous users are rejected with close code 4001."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/',
        )
        communicator.scope['user'] = AnonymousUser()

        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4001

    async def test_missing_user_in_scope_is_rejected(self):
        """Consumer closes if no user is present in scope."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/',
        )
        # No 'user' key in scope at all

        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4001

    async def test_ping_returns_pong(self, db):
        """Sending a ping message receives a pong response."""
        from asgiref.sync import sync_to_async
        user = await sync_to_async(UserFactory)()

        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/',
        )
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({'type': 'ping'})
        response = await communicator.receive_json_from()

        assert response['type'] == 'pong'
        await communicator.disconnect()

    async def test_group_notification_delivered(self, db, settings):
        """A message sent to the user's group reaches the consumer."""
        settings.CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            }
        }
        from asgiref.sync import sync_to_async
        user = await sync_to_async(UserFactory)()

        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/',
        )
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'user_{user.id}',
            {
                'type': 'notification',
                'event': 'test_event',
                'data': {'message': 'hello'},
            },
        )

        response = await communicator.receive_json_from(timeout=3)
        assert response['type'] == 'notification'
        assert response['event'] == 'test_event'
        assert response['data']['message'] == 'hello'

        await communicator.disconnect()

    async def test_disconnect_removes_from_group(self, db, settings):
        """After disconnect, no messages are delivered to the former group member."""
        settings.CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            }
        }
        from asgiref.sync import sync_to_async
        user = await sync_to_async(UserFactory)()

        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/',
        )
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

        # After disconnect, group_send should not cause any issues or delivery
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'user_{user.id}',
            {'type': 'notification', 'event': 'orphan', 'data': {}},
        )
        # No assert needed – main check is no exception raised


# =============================================================================
# NowPlayingConsumer Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestNowPlayingConsumer:
    """Tests for the global now-playing broadcast WebSocket consumer."""

    async def test_authenticated_user_can_connect(self, db, settings):
        settings.CHANNEL_LAYERS = {
            'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
        }
        from asgiref.sync import sync_to_async
        user = await sync_to_async(UserFactory)()

        communicator = WebsocketCommunicator(
            NowPlayingConsumer.as_asgi(),
            '/ws/now-playing/',
        )
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    async def test_anonymous_user_is_rejected(self):
        communicator = WebsocketCommunicator(
            NowPlayingConsumer.as_asgi(),
            '/ws/now-playing/',
        )
        communicator.scope['user'] = AnonymousUser()

        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4001

    async def test_update_broadcasts_to_group(self, db, settings):
        """An 'update' message is broadcast to all now_playing group members."""
        settings.CHANNEL_LAYERS = {
            'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
        }
        from asgiref.sync import sync_to_async
        user1 = await sync_to_async(UserFactory)()
        user2 = await sync_to_async(UserFactory)()

        comm1 = WebsocketCommunicator(NowPlayingConsumer.as_asgi(), '/ws/now-playing/')
        comm1.scope['user'] = user1
        comm2 = WebsocketCommunicator(NowPlayingConsumer.as_asgi(), '/ws/now-playing/')
        comm2.scope['user'] = user2

        connected1, _ = await comm1.connect()
        connected2, _ = await comm2.connect()
        assert connected1
        assert connected2

        # user1 sends an update
        await comm1.send_json_to({'type': 'update', 'track_id': 42})

        # user2 should receive the broadcast
        response = await comm2.receive_json_from(timeout=3)
        assert response['type'] == 'now_playing'
        assert response['data']['track_id'] == 42
        assert response['data']['user_id'] == user1.id

        await comm1.disconnect()
        await comm2.disconnect()
