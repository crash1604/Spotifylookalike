from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.serializers import serialize

from .models import Artist
from .serializers import ArtistSerializer

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_artists(request):
    artist_files = Artist.objects.all()

    # Serialize genres for each artist
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
        # Assuming you send artist data in the request data
        serializer = ArtistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_artist_by_name(request, artist_name):
    # Retrieve the artist or return a 404 response if not found
    artist = get_object_or_404(Artist, name__exact=artist_name)
    # Delete the artist
    artist.delete()
    return Response({'message': 'Artist deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def modify_artist_by_name(request, artist_name):
    # Retrieve the artist or return a 404 response if not found
    artist = get_object_or_404(Artist, name__exact=artist_name)

    # Update the artist data
    serializer = ArtistSerializer(artist, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
