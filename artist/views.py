"""
ViewSets for artist-related endpoints.
"""

import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.core.serializers import serialize
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Artist
from .serializers import ArtistSerializer, ArtistDetailSerializer, ArtistListSerializer
from music.serializers import TrackListSerializer
from core.permissions import IsAdminOrReadOnly
from core.pagination import StandardResultsSetPagination

logger = logging.getLogger('spotify')


@extend_schema_view(
    list=extend_schema(summary="List all artists", tags=['Artists']),
    retrieve=extend_schema(summary="Get artist details", tags=['Artists']),
    create=extend_schema(summary="Create an artist", tags=['Artists']),
    update=extend_schema(summary="Update an artist", tags=['Artists']),
    partial_update=extend_schema(summary="Partially update an artist", tags=['Artists']),
    destroy=extend_schema(summary="Delete an artist", tags=['Artists']),
)
class ArtistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Artist CRUD operations.
    """
    queryset = Artist.objects.prefetch_related('genres', 'tracks', 'album_set')
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['genres']
    search_fields = ['name', 'biography']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.action == 'list':
            return ArtistListSerializer
        return ArtistDetailSerializer

    @extend_schema(summary="Get artist's tracks", tags=['Artists'])
    @action(detail=True, methods=['get'])
    def tracks(self, request, pk=None):
        """Get all tracks by this artist."""
        artist = self.get_object()
        tracks = artist.tracks.filter(is_available=True)
        page = self.paginate_queryset(tracks)
        if page is not None:
            serializer = TrackListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Get artist's albums", tags=['Artists'])
    @action(detail=True, methods=['get'])
    def albums(self, request, pk=None):
        """Get all albums by this artist."""
        from album.serializers import AlbumListSerializer
        artist = self.get_object()
        albums = artist.album_set.all()
        page = self.paginate_queryset(albums)
        if page is not None:
            serializer = AlbumListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AlbumListSerializer(albums, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Get top artists", tags=['Artists'])
    @action(detail=False, methods=['get'])
    def top(self, request):
        """Get top artists by track play count."""
        from django.db.models import Sum
        artists = self.queryset.annotate(
            total_plays=Sum('tracks__play_count')
        ).order_by('-total_plays')[:20]
        serializer = ArtistListSerializer(artists, many=True)
        return Response(serializer.data)


# =============================================================================
# Legacy function-based views (deprecated)
# =============================================================================

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_artists(request):
    """Legacy endpoint - use /api/v1/artists/ instead."""
    artist_files = Artist.objects.all()
    data = []
    for artist in artist_files:
        genres_data = serialize('json', artist.genres.all())
        artist_data = {
            'name': artist.name,
            'biography': artist.biography,
            'genres': genres_data,
        }
        data.append(artist_data)
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_artist_by_name(request, artist_name):
    artist = Artist.objects.get(name__exact=artist_name)
    genres_list = [{'id': genre.id, 'name': genre.name} for genre in artist.genres.all()]
    data = {'name': artist.name, 'biography': artist.biography, 'genres': genres_list}
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_new_artist(request):
    if request.method == 'POST':
        serializer = ArtistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_artist_by_name(request, artist_name):
    artist = get_object_or_404(Artist, name__exact=artist_name)
    artist.delete()
    return Response({'message': 'Artist deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def modify_artist_by_name(request, artist_name):
    artist = get_object_or_404(Artist, name__exact=artist_name)
    serializer = ArtistSerializer(artist, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
