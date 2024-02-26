from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

from .models import Playlist
from music.models import Track

from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_playlists(request):
    playlist_files = Playlist.objects.all()

    # Manually construct the JSON response
    data = []
    for playlist in playlist_files:
        playlist_data = {
            'id': playlist.id,
            'title': playlist.title,
            'creation_date': playlist.creation_date,
            'owner': playlist.owner.username,  # Assuming you want to include the owner's username
            'cover_art': playlist.cover_art.url if playlist.cover_art else None,
            'track_list': [track.title for track in playlist.track_list.all()],  # Assuming many-to-many relationship with Track
            # Add other Playlist-related fields as needed
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
            'owner': playlist.owner.username,  # Assuming you want to include the owner's username
            'cover_art': playlist.cover_art.url if playlist.cover_art else None,
            'track_list': [track.title for track in playlist.track_list.all()],  # Assuming many-to-many relationship with Track
            # Add other Playlist-related fields as needed
        }
        data.append(playlist_data)
    return JsonResponse(data, safe=False)

@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_to_playlist_by_name(request, playlist_name):
    playlist = get_object_or_404(Playlist, title__exact=playlist_name)
    
    if request.method == 'PUT':
        # Assuming you send track IDs in the request data
        track_ids = request.data.get('track_ids', [])
        
        # Retrieve the tracks with the given IDs
        tracks = Track.objects.filter(id__in=track_ids)

        # Add the retrieved tracks to the playlist's track_list
        playlist.track_list.add(*tracks)

        return Response({'message': f'Tracks added to {playlist.title} successfully'})