"""
ViewSets for playlist-related endpoints.
"""

import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Playlist
from .serializers import PlaylistSerializer, PlaylistDetailSerializer, PlaylistListSerializer
from music.models import Track
from music.serializers import TrackListSerializer
from core.permissions import IsOwnerOrReadOnly
from core.pagination import StandardResultsSetPagination

logger = logging.getLogger('spotify')


@extend_schema_view(
    list=extend_schema(summary="List all playlists", tags=['Playlists']),
    retrieve=extend_schema(summary="Get playlist details", tags=['Playlists']),
    create=extend_schema(summary="Create a playlist", tags=['Playlists']),
    update=extend_schema(summary="Update a playlist", tags=['Playlists']),
    partial_update=extend_schema(summary="Partially update a playlist", tags=['Playlists']),
    destroy=extend_schema(summary="Delete a playlist", tags=['Playlists']),
)
class PlaylistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Playlist CRUD operations.
    """
    queryset = Playlist.objects.select_related('owner').prefetch_related('track_list')
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['owner', 'is_public']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'updated_at']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PlaylistListSerializer
        return PlaylistDetailSerializer

    def get_queryset(self):
        """Filter playlists based on visibility."""
        user = self.request.user
        if user.is_authenticated:
            # Show user's own playlists and public playlists
            return Playlist.objects.filter(
                models.Q(owner=user) | models.Q(is_public=True)
            ).select_related('owner').prefetch_related('track_list')
        return Playlist.objects.filter(is_public=True)

    def perform_create(self, serializer):
        """Set the owner to the current user."""
        serializer.save(owner=self.request.user)

    @extend_schema(summary="Get playlist tracks", tags=['Playlists'])
    @action(detail=True, methods=['get'])
    def tracks(self, request, pk=None):
        """Get all tracks in this playlist."""
        playlist = self.get_object()
        tracks = playlist.track_list.filter(is_available=True)
        page = self.paginate_queryset(tracks)
        if page is not None:
            serializer = TrackListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Add tracks to playlist", tags=['Playlists'])
    @action(detail=True, methods=['post'])
    def add_tracks(self, request, pk=None):
        """Add tracks to the playlist."""
        playlist = self.get_object()
        track_ids = request.data.get('track_ids', [])
        tracks = Track.objects.filter(id__in=track_ids, is_available=True)
        playlist.track_list.add(*tracks)
        return Response({
            'message': f'Added {tracks.count()} tracks to {playlist.title}',
            'track_count': playlist.track_list.count()
        })

    @extend_schema(summary="Remove tracks from playlist", tags=['Playlists'])
    @action(detail=True, methods=['post'])
    def remove_tracks(self, request, pk=None):
        """Remove tracks from the playlist."""
        playlist = self.get_object()
        track_ids = request.data.get('track_ids', [])
        tracks = Track.objects.filter(id__in=track_ids)
        playlist.track_list.remove(*tracks)
        return Response({
            'message': f'Removed tracks from {playlist.title}',
            'track_count': playlist.track_list.count()
        })

    @extend_schema(summary="Get user's playlists", tags=['Playlists'])
    @action(detail=False, methods=['get'])
    def mine(self, request):
        """Get current user's playlists."""
        playlists = Playlist.objects.filter(owner=request.user)
        page = self.paginate_queryset(playlists)
        if page is not None:
            serializer = PlaylistListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PlaylistListSerializer(playlists, many=True)
        return Response(serializer.data)


# Import models for Q object
from django.db import models


# =============================================================================
# Legacy function-based views (deprecated)
# =============================================================================

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_playlists(request):
    """Legacy endpoint - use /api/v1/playlists/ instead."""
    playlist_files = Playlist.objects.all()
    data = []
    for playlist in playlist_files:
        playlist_data = {
            'id': playlist.id,
            'title': playlist.title,
            'creation_date': playlist.creation_date,
            'owner': playlist.owner.username,
            'cover_art': playlist.cover_art.url if playlist.cover_art else None,
            'track_list': [track.title for track in playlist.track_list.all()],
        }
        data.append(playlist_data)
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_playlist_by_name(request, playlist_name):
    playlists = Playlist.objects.filter(title__icontains=playlist_name)
    data = []
    for playlist in playlists:
        playlist_data = {
            'id': playlist.id,
            'title': playlist.title,
            'creation_date': playlist.creation_date,
            'owner': playlist.owner.username,
            'cover_art': playlist.cover_art.url if playlist.cover_art else None,
            'track_list': [track.title for track in playlist.track_list.all()],
        }
        data.append(playlist_data)
    return JsonResponse(data, safe=False)


@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_to_playlist_by_name(request, playlist_name):
    playlist = get_object_or_404(Playlist, title__exact=playlist_name)
    if request.method == 'PUT':
        track_ids = request.data.get('track_ids', [])
        tracks = Track.objects.filter(id__in=track_ids)
        playlist.track_list.add(*tracks)
        return Response({'message': f'Tracks added to {playlist.title} successfully'})


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def remove_from_playlist_by_name(request, playlist_name):
    playlist = get_object_or_404(Playlist, title__exact=playlist_name)
    if request.method == 'DELETE':
        track_ids = request.data.get('track_ids', [])
        tracks = Track.objects.filter(id__in=track_ids)
        playlist.track_list.remove(*tracks)
        return Response({'message': f'Tracks removed from {playlist.title} successfully'})


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_new_playlist(request):
    if request.method == 'POST':
        request.data['owner'] = request.user.id
        serializer = PlaylistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    return Response({'error': 'Method not allowed'}, status=405)


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_playlist_by_name(request, playlist_name):
    if request.method == "DELETE":
        playlist = get_object_or_404(Playlist, title__exact=playlist_name)
        playlist.delete()
        return JsonResponse({'success': 'Playlist deleted successfully'}, status=200)
    return JsonResponse({'error': 'DELETE request required'}, status=400)
