from django.shortcuts import render
from django.http import JsonResponse

from .models import Artist

from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_artists(request):
    artist_files = Artist.objects.all()
    data = [{'name': artist.name, 'biography': artist.biography, 'genres': artist.genres} for artist in artist_files]
    return JsonResponse(data, safe=False)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_artist_by_name(request, artist_name):
    artist = Artist.objects.get(name__exact=artist_name)
    genres_list = [{'id': genre.id, 'name': genre.name} for genre in artist.genres.all()]
    data = {'name': artist.name, 'biography': artist.biography, 'genres': genres_list}
    return JsonResponse(data, safe=False)
