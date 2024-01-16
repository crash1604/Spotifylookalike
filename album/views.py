from django.shortcuts import render
from django.http import JsonResponse

from .models import Album
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
def get_album_by_name(request, album_name):
    album_files = Album.objects.filter(title__icontains=album_name)
    data = [{'title': album.title, 'artist': album.artist.name} for album in album_files]
    return JsonResponse(data, safe=False)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_album_by_artist(request, artist_name):
    # Artist = apps.get_app_config('artist').get_model('Artist')
    artistName = Artist.objects.get(name = artist_name)
    album_files = Album.objects.filter(artist=artistName)
    data = [{'title': album.title, 'artist': album.artist.name} for album in album_files]
    return JsonResponse(data, safe=False)


