"""
Custom exception handling for consistent API error responses.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db import IntegrityError

logger = logging.getLogger('spotify')


class APIException(Exception):
    """Base exception for API errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = 'An unexpected error occurred.'
    default_code = 'error'

    def __init__(self, message=None, code=None, status_code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        if status_code:
            self.status_code = status_code


class NotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = 'Resource not found.'
    default_code = 'not_found'


class ValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = 'Invalid input data.'
    default_code = 'validation_error'


class AuthenticationError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = 'Authentication credentials were not provided or are invalid.'
    default_code = 'authentication_error'


class PermissionDeniedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = 'You do not have permission to perform this action.'
    default_code = 'permission_denied'


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_message = 'Resource already exists.'
    default_code = 'conflict'


class RateLimitError(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = 'Too many requests. Please try again later.'
    default_code = 'rate_limit_exceeded'


class StreamingError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = 'Error streaming audio file.'
    default_code = 'streaming_error'


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.

    Response format:
    {
        "error": {
            "code": "error_code",
            "message": "Human readable message",
            "details": {} (optional)
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Get request info for logging
    request = context.get('request')
    view = context.get('view')

    # Handle custom API exceptions
    if isinstance(exc, APIException):
        logger.warning(
            f"API Exception: {exc.code} - {exc.message}",
            extra={
                'status_code': exc.status_code,
                'path': request.path if request else None,
                'method': request.method if request else None,
            }
        )
        return Response(
            {
                'error': {
                    'code': exc.code,
                    'message': exc.message,
                }
            },
            status=exc.status_code
        )

    # Handle Django's Http404
    if isinstance(exc, Http404):
        return Response(
            {
                'error': {
                    'code': 'not_found',
                    'message': str(exc) or 'Resource not found.',
                }
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                'error': {
                    'code': 'validation_error',
                    'message': 'Invalid input data.',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Handle database integrity errors
    if isinstance(exc, IntegrityError):
        logger.error(f"Database integrity error: {str(exc)}")
        return Response(
            {
                'error': {
                    'code': 'conflict',
                    'message': 'A resource with this data already exists.',
                }
            },
            status=status.HTTP_409_CONFLICT
        )

    # If DRF handled the exception, format it consistently
    if response is not None:
        error_message = 'An error occurred.'
        error_code = 'error'
        details = None

        if isinstance(response.data, dict):
            if 'detail' in response.data:
                error_message = str(response.data['detail'])
                error_code = response.data.get('code', 'error')
            else:
                details = response.data
                error_message = 'Validation failed.'
                error_code = 'validation_error'
        elif isinstance(response.data, list):
            error_message = response.data[0] if response.data else 'An error occurred.'

        formatted_response = {
            'error': {
                'code': error_code,
                'message': error_message,
            }
        }
        if details:
            formatted_response['error']['details'] = details

        response.data = formatted_response
        return response

    # Log unhandled exceptions
    logger.exception(
        f"Unhandled exception in {view.__class__.__name__ if view else 'unknown'}: {str(exc)}",
        extra={
            'path': request.path if request else None,
            'method': request.method if request else None,
        }
    )

    # Return generic error for unhandled exceptions
    return Response(
        {
            'error': {
                'code': 'internal_error',
                'message': 'An unexpected error occurred. Please try again later.',
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
