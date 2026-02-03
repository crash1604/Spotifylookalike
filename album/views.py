"""
ViewSets for album-related endpoints.
"""

import logging
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Album
from .serializers import AlbumSerializer, AlbumDetailSerializer, AlbumListSerializer
from music.models import Track
from music.serializers import TrackListSerializer, TrackSerializer
from artist.models import Artist
from core.permissions import IsAdminOrReadOnly
from core.pagination import StandardResultsSetPagination

logger = logging.getLogger('spotify')


@extend_schema_view(
    list=extend_schema(summary="List all albums", tags=['Albums']),
    retrieve=extend_schema(summary="Get album details", tags=['Albums']),
    create=extend_schema(summary="Create an album", tags=['Albums']),
    update=extend_schema(summary="Update an album", tags=['Albums']),
    partial_update=extend_schema(summary="Partially update an album", tags=['Albums']),
    destroy=extend_schema(summary="Delete an album", tags=['Albums']),
)
class AlbumViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Album CRUD operations.
    """
    queryset = Album.objects.select_related('artist').prefetch_related('tracks')
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'artist': ['exact'],
        'artist__name': ['exact', 'icontains'],
        'release_date': ['exact', 'gte', 'lte', 'year'],
    }
    search_fields = ['title', 'artist__name']
    ordering_fields = ['title', 'release_date', 'created_at']
    ordering = ['-release_date']

    def get_serializer_class(self):
        if self.action == 'list':
            return AlbumListSerializer
        return AlbumDetailSerializer

    @extend_schema(summary="Get album tracks", tags=['Albums'])
    @action(detail=True, methods=['get'])
    def tracks(self, request, pk=None):
        """Get all tracks in this album."""
        album = self.get_object()
        tracks = album.tracks.filter(is_available=True).order_by('disc_number', 'track_number')
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Get new releases", tags=['Albums'])
    @action(detail=False, methods=['get'])
    def new_releases(self, request):
        """Get recently released albums."""
        albums = self.queryset.order_by('-release_date')[:20]
        serializer = AlbumListSerializer(albums, many=True)
        return Response(serializer.data)


# =============================================================================
# Legacy function-based views (deprecated)
# =============================================================================

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_albums(request):
    """Legacy endpoint - use /api/v1/albums/ instead."""
    album_files = Album.objects.all()
    data = [{'title': album.title, 'artist': album.artist.name} for album in album_files]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_album_by_artist_and_name(request, artist_name, album_name):
    album = Album.objects.get(artist__name__exact=artist_name, title__exact=album_name)
    serializer = AlbumSerializer(album)
    return JsonResponse(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_album_by_artist(request, artist_name):
    artistName = Artist.objects.get(name=artist_name)
    album_files = Album.objects.filter(artist=artistName)
    data = [{'title': album.title, 'artist': album.artist.name} for album in album_files]
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_new_album(request):
    if request.method == "POST":
        title = request.data.get('title')
        release_date = datetime.strptime(request.data.get('release_date'), '%Y-%m-%d')
        artist_id = request.data.get('artist')
        cover_art = request.data.get('cover_art')

        album = Album.objects.create(
            title=title,
            release_date=release_date,
            artist_id=artist_id,
            cover_art=cover_art
        )

        data = {
            'title': album.title,
            'release_date': str(album.release_date),
            'artist': album.artist.name,
            'cover_art': album.cover_art.url if album.cover_art else None,
        }
        return JsonResponse(data, status=201)
    return JsonResponse({'error': 'POST request required'}, status=405)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tracks_by_album_name_and_artist(request, artist_name, album_name):
    album = get_object_or_404(Album, title__iexact=album_name, artist__name__exact=artist_name)
    trackList = Track.objects.filter(album=album)
    serializer = TrackSerializer(trackList, many=True)
    return JsonResponse(serializer.data, safe=False)
