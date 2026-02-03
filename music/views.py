"""
ViewSets for music-related endpoints.

Uses Django REST Framework ViewSets for:
- Automatic URL routing
- Standardized CRUD operations
- Filtering, search, and ordering
- Proper pagination
"""

import logging
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import Track, Genre
from artist.models import Artist
from album.models import Album
from .serializers import (
    TrackListSerializer,
    TrackDetailSerializer,
    TrackCreateUpdateSerializer,
    GenreSerializer,
    TrackSerializer
)
from core.permissions import IsAdminOrReadOnly
from core.pagination import StandardResultsSetPagination

logger = logging.getLogger('spotify')


@extend_schema_view(
    list=extend_schema(
        summary="List all tracks",
        description="Get a paginated list of all tracks with filtering and search.",
        tags=['Tracks']
    ),
    retrieve=extend_schema(
        summary="Get track details",
        description="Get detailed information about a specific track.",
        tags=['Tracks']
    ),
    create=extend_schema(
        summary="Create a new track",
        description="Upload and create a new track. Requires admin privileges.",
        tags=['Tracks']
    ),
    update=extend_schema(
        summary="Update a track",
        description="Update all fields of a track. Requires admin privileges.",
        tags=['Tracks']
    ),
    partial_update=extend_schema(
        summary="Partially update a track",
        description="Update specific fields of a track. Requires admin privileges.",
        tags=['Tracks']
    ),
    destroy=extend_schema(
        summary="Delete a track",
        description="Delete a track. Requires admin privileges.",
        tags=['Tracks']
    ),
)
class TrackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Track CRUD operations.

    Provides:
    - list: GET /tracks/
    - retrieve: GET /tracks/{id}/
    - create: POST /tracks/
    - update: PUT /tracks/{id}/
    - partial_update: PATCH /tracks/{id}/
    - destroy: DELETE /tracks/{id}/
    """
    queryset = Track.objects.select_related(
        'artist', 'album', 'genre'
    ).filter(is_available=True)
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'artist': ['exact'],
        'artist__name': ['exact', 'icontains'],
        'album': ['exact'],
        'album__title': ['exact', 'icontains'],
        'genre': ['exact'],
        'genre__name': ['exact', 'icontains'],
        'explicit': ['exact'],
        'release_date': ['exact', 'gte', 'lte', 'year'],
    }
    search_fields = ['title', 'artist__name', 'album__title', 'lyrics']
    ordering_fields = ['title', 'release_date', 'play_count', 'created_at', 'duration']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TrackListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TrackCreateUpdateSerializer
        return TrackDetailSerializer

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        """List tracks with caching."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Get track details."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        summary="Get top tracks",
        description="Get the most played tracks.",
        tags=['Tracks'],
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                description='Number of tracks to return (default: 20, max: 100)'
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def top(self, request):
        """Get top played tracks."""
        limit = min(int(request.query_params.get('limit', 20)), 100)
        tracks = self.queryset.order_by('-play_count')[:limit]
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get recent tracks",
        description="Get recently added tracks.",
        tags=['Tracks']
    )
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently added tracks."""
        tracks = self.queryset.order_by('-created_at')[:20]
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get tracks by genre",
        description="Get all tracks in a specific genre.",
        tags=['Tracks']
    )
    @action(detail=False, methods=['get'], url_path='genre/(?P<genre_slug>[^/.]+)')
    def by_genre(self, request, genre_slug=None):
        """Get tracks by genre slug."""
        tracks = self.queryset.filter(genre__slug=genre_slug)
        page = self.paginate_queryset(tracks)
        if page is not None:
            serializer = TrackListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Increment play count",
        description="Record a play event for the track.",
        tags=['Tracks']
    )
    @action(detail=True, methods=['post'])
    def play(self, request, pk=None):
        """Increment play count when a track is played."""
        track = self.get_object()
        Track.objects.filter(pk=pk).update(play_count=F('play_count') + 1)
        track.refresh_from_db()
        return Response({'play_count': track.play_count})


@extend_schema_view(
    list=extend_schema(summary="List all genres", tags=['Genres']),
    retrieve=extend_schema(summary="Get genre details", tags=['Genres']),
    create=extend_schema(summary="Create a genre", tags=['Genres']),
    update=extend_schema(summary="Update a genre", tags=['Genres']),
    destroy=extend_schema(summary="Delete a genre", tags=['Genres']),
)
class GenreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Genre CRUD operations.
    """
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']
    lookup_field = 'slug'

    @extend_schema(
        summary="Get genre tracks",
        description="Get all tracks in this genre.",
        tags=['Genres']
    )
    @action(detail=True, methods=['get'])
    def tracks(self, request, slug=None):
        """Get all tracks in a genre."""
        genre = self.get_object()
        tracks = Track.objects.filter(genre=genre, is_available=True)
        page = self.paginate_queryset(tracks)
        if page is not None:
            serializer = TrackListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)


# =============================================================================
# Legacy function-based views for backward compatibility
# These endpoints are deprecated and will be removed in v2
# =============================================================================

from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from datetime import datetime, timedelta


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_tracks(request):
    """Legacy endpoint - use /api/v1/tracks/ instead."""
    music_files = Track.objects.all()
    serializer = TrackSerializer(music_files, many=True)
    return JsonResponse(serializer.data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tracks_by_name(request, track_name):
    """Legacy endpoint - use /api/v1/tracks/?search={name} instead."""
    tracks = Track.objects.filter(title__icontains=track_name)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tracks_by_artist_name(request, artist_name):
    artist = Artist.objects.get(name=artist_name)
    tracks = Track.objects.filter(artist=artist)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tracks_by_genre(request, genre):
    genre_name = Genre.objects.get(name=genre)
    tracks = Track.objects.filter(genre=genre_name)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tracks_by_album(request, album_name):
    album = Album.objects.get(title=album_name)
    tracks = Track.objects.filter(album=album)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_artists(requests):
    artists = Artist.objects.all()
    data = [{'name': artist.name, 'biography': artist.biography} for artist in artists]
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_track(request):
    if request.method == "POST":
        title = request.data.get('title')
        artist_id = request.data.get('artist')
        album_id = request.data.get('album')
        duration = timedelta(
            hours=int(request.data.get('duration').split(":")[0]),
            minutes=int(request.data.get('duration').split(":")[1]),
            seconds=int(request.data.get('duration').split(":")[2])
        )
        release_date = datetime.strptime(request.data.get('release_date'), '%Y-%d-%m')
        genre_id = request.data.get('genre')
        audio_file = request.data.get('audio_file')

        track = Track.objects.create(
            title=title,
            artist_id=artist_id,
            album_id=album_id,
            duration=duration,
            release_date=release_date,
            genre_id=genre_id,
            audio_file=audio_file
        )

        data = {
            'title': track.title,
            'artist': track.artist.name,
            'album': track.album.title,
            'duration': str(track.duration),
            'release_date': str(track.release_date),
            'genre': track.genre.name,
            'audio_file': track.audio_file.url,
        }
        return JsonResponse(data, status=201)
    return JsonResponse({'error': 'POST request required'}, status=400)


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_track(request, track_name):
    if request.method == "DELETE":
        track = get_object_or_404(Track, title=track_name)
        if not request.user.is_staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        track.delete()
        return JsonResponse({'success': 'Track deleted successfully'}, status=200)
    return JsonResponse({'error': 'DELETE request required'}, status=400)


@api_view(['PUT', 'PATCH'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_track(request, track_name):
    try:
        track = Track.objects.get(title=track_name)
    except Track.DoesNotExist:
        return JsonResponse({'error': f'Track not found: {track_name}'}, status=status.HTTP_404_NOT_FOUND)

    if request.method in ['PUT', 'PATCH']:
        if 'title' in request.data:
            track.title = request.data['title']
        if 'duration' in request.data:
            track.duration = timedelta(
                hours=int(request.data.get('duration').split(":")[0]),
                minutes=int(request.data.get('duration').split(":")[1]),
                seconds=int(request.data.get('duration').split(":")[2])
            )
        if 'release_date' in request.data:
            track.release_date = datetime.strptime(request.data.get('release_date'), '%Y-%d-%m')
        if 'audio_file' in request.data:
            track.audio_file = request.data['audio_file']
        if 'artist' in request.data:
            track.artist_id = request.data['artist']
        if 'album' in request.data:
            track.album_id = request.data['album']
        if 'genre' in request.data:
            track.genre_id = request.data['genre']

        track.save()
        return JsonResponse({'success': f'Track updated: {track_name}'}, status=status.HTTP_200_OK)

    return JsonResponse({'error': 'PUT or PATCH request required'}, status=status.HTTP_400_BAD_REQUEST)
