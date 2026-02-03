"""
Serializers for artist-related models.
"""

from rest_framework import serializers
from .models import Artist
from music.models import Genre


class ArtistListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for artist listings."""
    genre_names = serializers.SerializerMethodField()
    track_count = serializers.SerializerMethodField()
    album_count = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = ['id', 'name', 'genre_names', 'track_count', 'album_count']

    def get_genre_names(self, obj):
        return [genre.name for genre in obj.genres.all()]

    def get_track_count(self, obj):
        return obj.tracks.count()

    def get_album_count(self, obj):
        return obj.album_set.count()


class ArtistDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual artist view."""
    genre_names = serializers.SerializerMethodField()
    genres = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        required=False
    )
    track_count = serializers.SerializerMethodField()
    album_count = serializers.SerializerMethodField()
    total_plays = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = [
            'id', 'name', 'biography', 'genres', 'genre_names',
            'track_count', 'album_count', 'total_plays', 'created_at'
        ]

    def get_genre_names(self, obj):
        return [genre.name for genre in obj.genres.all()]

    def get_track_count(self, obj):
        return obj.tracks.count()

    def get_album_count(self, obj):
        return obj.album_set.count()

    def get_total_plays(self, obj):
        from django.db.models import Sum
        return obj.tracks.aggregate(total=Sum('play_count'))['total'] or 0


class ArtistSerializer(serializers.ModelSerializer):
    """Legacy serializer for backward compatibility."""
    class Meta:
        model = Artist
        fields = '__all__'
