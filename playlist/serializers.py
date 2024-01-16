from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Playlist
from music.models import Track
from artist.models import Artist
from album.models import Album

class TrackSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Track
        fields = ['id', 'title', 'artist', 'album', 'duration', 'release_date', 'genre', 'audio_file']

class PlaylistSerializer(serializers.ModelSerializer):
    track_list = TrackSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        fields = ['title', 'creation_date', 'owner', 'cover_art', 'track_list']
        
class UserSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = User
        fields = ['id', 'username', 'password', 'email']
        
class ArtistSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Artist
        fields = ['name', 'biography', 'genres']
        
class AlbumSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Album
        fields = ['title', 'artist', 'genres', 'release_date', 'cover_art']
