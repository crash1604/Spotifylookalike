from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from datetime import datetime

from .models import Album
from music.models import Track
from music.serializers import TrackSerializer
from .serializers import AlbumSerializer
from artist.models import Artist

from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_albums(request):
    album_files = Album.objects.all()
    data = [{'title': album.title, 'artist': album.artist.name} for album in album_files]
    return JsonResponse(data, safe=False)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_album_by_artist_and_name(request,artist_name , album_name):
    album = Album.objects.get(artist__name__exact=artist_name, title__exact=album_name)
    serializer = AlbumSerializer(album)  
    return JsonResponse(serializer.data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_album_by_artist(request, artist_name):
    # Artist = apps.get_app_config('artist').get_model('Artist')
    artistName = Artist.objects.get(name = artist_name)
    album_files = Album.objects.filter(artist=artistName)
    data = [{'title': album.title, 'artist': album.artist.name} for album in album_files]
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_new_album(request):
    if request.method == "POST":
        title = request.data.get('title')
        release_date = datetime.strptime(request.data.get('release_date'),'%Y-%m-%d')
        artist_id = request.data.get('artist')
        cover_art = request.data.get('cover_art')

        # Create a new Album object
        album = Album.objects.create(
            title=title,
            release_date=release_date,
            artist_id=artist_id,
            cover_art=cover_art
        )

        # Return a JSON response with the created album data
        data = {
            'title': album.title,
            'release_date': str(album.release_date),
            'artist': album.artist.name,
            'cover_art': album.cover_art.url if album.cover_art else None,
        }
        return JsonResponse(data, status=201)

    else:
        return JsonResponse({'error': 'This view requires a POST request'}, status=405)
    

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tracks_by_album_name_and_artist(request, artist_name, album_name):
    album = get_object_or_404(Album, title__iexact=album_name, artist__name__exact=artist_name)
    trackList = Track.objects.filter(album=album)
    serializer = TrackSerializer(trackList, many=True)
    return JsonResponse(serializer.data, safe=False)
