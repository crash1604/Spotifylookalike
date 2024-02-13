from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Track, Artist, Album

class TrackSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Track
        fields = '__all__'
        
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
