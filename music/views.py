from django.shortcuts import render
from django.http import JsonResponse

from .models import Track, Artist, Genre, Album

# Create your views here.

def get_all_tracks(request):
    music_files = Track.objects.all()
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in music_files]
    return JsonResponse(data, safe=False)

def get_tracks_by_name(request, track_name):
    tracks = Track.objects.filter(title__icontains=track_name)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)

def get_tracks_by_artist_name(request, artist_name):
    artist = Artist.objects.get(name=artist_name)
    tracks = Track.objects.filter(artist=artist)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)

def get_tracks_by_genre(request, genre):
    genre_name = Genre.objects.get(name=genre)
    tracks = Track.objects.filter(genre=genre_name)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)

def get_tracks_by_album(request, album_name):
    album = Album.objects.get(title=album_name)
    tracks = Track.objects.filter(album=album)
    data = [{'title': track.title, 'artist': track.artist.name, 'album': track.album.title} for track in tracks]
    return JsonResponse(data, safe=False)