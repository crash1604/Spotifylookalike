from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Track, Artist, Genre, Album
from .serializers import TrackSerializer

from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from datetime import datetime, timedelta

# Supplimental functions

def get_track_id_by_name(track_name):
    track_id = Track.objects.filter(title=track_name).values_list('id', flat=True).first()
    return track_id

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_tracks(request):
    music_files = Track.objects.all()
    # data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in music_files]
    serializer = TrackSerializer(music_files, many=True)
    return JsonResponse(serializer.data, safe=False)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tracks_by_name(request, track_name):
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

# Read
# get artists
@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_artists(requests):
    print("inside get artists")
    artists = Artist.objects.all()
    print(Artist.objects.all())
    data = [{'name': artist.name, 'biography': artist.biography } for artist in artists]
    print(data)
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_track(request): 
    if request.method =="POST":
        title = request.data.get('title')
        artist_id = request.data.get('artist')
        album_id = request.data.get('album')
        duration = timedelta(
            hours=int(request.data.get('duration').split(":")[0]),
            minutes=int(request.data.get('duration').split(":")[1]),
            seconds=int(request.data.get('duration').split(":")[2])
            )
        release_date = datetime.strptime(request.data.get('release_date'),'%Y-%d-%m')
        genre_id = request.data.get('genre')
        audio_file = request.data.get('audio_file')

            # Create a new Track object
        track = Track.objects.create(
            title=title,
            artist_id=artist_id,
            album_id=album_id,
            duration=duration,
            release_date=release_date,
            genre_id=genre_id,
            audio_file=audio_file
        )

            # Return a JSON response with the created track data
        data = {
                'title': track.title,
                'artist': track.artist.name,
                'album': track.album.title,
                'duration': str(track.duration),
                'release_date': str(track.release_date),
                'genre': track.genre.name,
                'audio_file': track.audio_file.url,  # Assuming 'audio_file' is a FileField
            }
        return JsonResponse(data, status=201)
    else:
        return "this page needs a POST request"
    
@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_track(request, track_name):
    if request.method == "DELETE":
        # Retrieve the track instance or return a 404 response if not found
        track = get_object_or_404(Track, title=track_name)

        # Check if the user has permission to delete the track (optional)
        # You may want to customize this based on your authentication logic
        if not request.user.has_perm('delete_track', track):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        # Delete the track
        track.delete()

        return JsonResponse({'success': 'Track deleted successfully'}, status=200)
    else:
        return JsonResponse({'error': 'This view requires a DELETE request'}, status=400)
