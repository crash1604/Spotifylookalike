from rest_framework import serializers
from django.contrib.auth.models import User
from music.models import Track

class UserSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = User
        fields = ['id', 'username', 'password', 'email']
        
class TrackSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Track
        fields = ['id', 'title', 'artist', 'album', 'duration', 'release_date', 'genre', 'audio_file']
        

