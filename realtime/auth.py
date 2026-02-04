"""
Custom Channels authentication middleware for JWT-based WebSocket auth.

WebSocket connections cannot use HTTP headers the same way REST does,
so the JWT token is passed as a query-string parameter:

    ws://host/ws/notifications/?token=<access_token>
"""

import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger('realtime')


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate a JWT access token and return the corresponding User."""
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth import get_user_model

        access = AccessToken(token_str)
        User = get_user_model()
        return User.objects.get(id=access['user_id'])
    except Exception as exc:
        logger.debug('WS auth failed: %s', exc)
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    ASGI middleware that reads a JWT from the ``token`` query parameter
    and attaches the authenticated user to ``scope['user']``.
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token', [])

        if token_list:
            scope['user'] = await get_user_from_token(token_list[0])
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)
