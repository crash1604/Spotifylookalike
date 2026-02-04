"""
spotify URL Configuration - Production Ready

API Structure:
- /api/v1/ - Versioned API endpoints (recommended)
- /health/ - Health check endpoints
- /admin/ - Django admin
- Legacy endpoints maintained for backward compatibility
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .views import home_page
from music.views import TrackViewSet, GenreViewSet
from artist.views import ArtistViewSet
from album.views import AlbumViewSet
from playlist.views import PlaylistViewSet

# =============================================================================
# API Router Configuration
# =============================================================================

router = DefaultRouter()
router.register(r'tracks', TrackViewSet, basename='track')
router.register(r'genres', GenreViewSet, basename='genre')
router.register(r'artists', ArtistViewSet, basename='artist')
router.register(r'albums', AlbumViewSet, basename='album')
router.register(r'playlists', PlaylistViewSet, basename='playlist')


# =============================================================================
# URL Patterns
# =============================================================================

urlpatterns = [
    # Home
    path('', home_page, name='home'),

    # Admin
    path('admin/', admin.site.urls),

    # ==========================================================================
    # API v1 Endpoints (Production)
    # ==========================================================================
    path('api/v1/', include([
        # Router-based endpoints
        path('', include(router.urls)),

        # JWT Authentication
        path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

        # Authentication (custom endpoints)
        path('auth/', include('authentication.urls')),

        # Streaming
        path('stream/', include('streaming.urls')),

        # Transcoding (admin-only)
        path('transcode/', include('transcoding.urls')),

        # Search (Elasticsearch-powered with ORM fallback)
        path('search/', include('search.urls')),
    ])),

    # ==========================================================================
    # API Documentation
    # ==========================================================================
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # ==========================================================================
    # Health Checks
    # ==========================================================================
    path('health/', include('health_check.urls')),

    # ==========================================================================
    # Legacy Endpoints (Deprecated - use /api/v1/ instead)
    # Maintained for backward compatibility
    # ==========================================================================
    path('album/', include('album.urls')),
    path('artist/', include('artist.urls')),
    path('auth/', include('authentication.urls')),
    path('music/', include('music.urls')),
    path('playlist/', include('playlist.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
