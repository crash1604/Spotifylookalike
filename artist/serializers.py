from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Artist
        
class ArtistSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Artist
        fields = '__all__'
