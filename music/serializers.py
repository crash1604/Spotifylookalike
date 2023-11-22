from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Track

class TrackSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Track
        fields = ['id', 'title', 'artist', 'album', 'duration', 'release_date', 'genre', 'audio_file']
        
class UserSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = User
        fields = ['id', 'username', 'password', 'email']
        