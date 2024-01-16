from django.shortcuts import render
from django.http import JsonResponse

from .models import Playlist

from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

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