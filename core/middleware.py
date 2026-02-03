"""
Custom middleware for the application.
"""

import time
import logging
import uuid
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('spotify')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all incoming requests and their response times.
    Useful for debugging, monitoring, and performance analysis.
    """

    def process_request(self, request):
        """Store the start time and request ID."""
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())[:8]

        # Log incoming request
        logger.info(
            f"[{request.request_id}] {request.method} {request.path}",
            extra={
                'request_id': request.request_id,
                'method': request.method,
                'path': request.path,
                'user': str(request.user) if hasattr(request, 'user') else 'anonymous',
                'ip': self.get_client_ip(request),
            }
        )

    def process_response(self, request, response):
        """Log response and calculate request duration."""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            duration_ms = round(duration * 1000, 2)

            # Add timing header for debugging
            response['X-Request-Duration-Ms'] = str(duration_ms)
            response['X-Request-ID'] = getattr(request, 'request_id', 'unknown')

            # Log response
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                f"[{getattr(request, 'request_id', 'unknown')}] "
                f"{request.method} {request.path} -> {response.status_code} "
                f"({duration_ms}ms)",
                extra={
                    'request_id': getattr(request, 'request_id', 'unknown'),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                }
            )

        return response

    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class CacheControlMiddleware(MiddlewareMixin):
    """
    Middleware to add appropriate cache control headers.
    """

    # Paths that should not be cached
    NO_CACHE_PATHS = ['/api/v1/auth/', '/admin/']

    # Paths that can be cached for longer
    STATIC_PATHS = ['/static/', '/media/']

    def process_response(self, request, response):
        path = request.path

        # No cache for authentication and admin
        if any(path.startswith(p) for p in self.NO_CACHE_PATHS):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        # Cache static files
        elif any(path.startswith(p) for p in self.STATIC_PATHS):
            response['Cache-Control'] = 'public, max-age=31536000'  # 1 year

        # Default API responses - cache for 5 minutes
        elif path.startswith('/api/'):
            if request.method == 'GET' and response.status_code == 200:
                response['Cache-Control'] = 'private, max-age=300'

        return response
