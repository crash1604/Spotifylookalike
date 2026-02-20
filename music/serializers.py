"""
Serializers for music-related models.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Track, Genre
from artist.models import Artist
from album.models import Album


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for Genre model."""
    track_count = serializers.SerializerMethodField()

    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug', 'description', 'track_count']
        read_only_fields = ['id', 'slug', 'track_count']

    def get_track_count(self, obj):
        # Use annotated value when available (avoids N+1 on list views)
        if hasattr(obj, 'track_count'):
            return obj.track_count
        return obj.tracks.count()


class TrackListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for track listings.
    Used in lists to reduce payload size.
    """
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    album_title = serializers.CharField(source='album.title', read_only=True)
    album_cover = serializers.ImageField(source='album.cover_art', read_only=True)
    genre_name = serializers.CharField(source='genre.name', read_only=True)
    formatted_duration = serializers.CharField(read_only=True)

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'artist_name', 'album_title', 'album_cover',
            'genre_name', 'formatted_duration', 'duration', 'explicit',
            'play_count', 'is_available'
        ]


class TrackDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual track view.
    Includes all metadata.
    """
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_id = serializers.IntegerField(source='artist.id', read_only=True)
    album_title = serializers.CharField(source='album.title', read_only=True)
    album_id = serializers.IntegerField(source='album.id', read_only=True)
    album_cover = serializers.ImageField(source='album.cover_art', read_only=True)
    genre_name = serializers.CharField(source='genre.name', read_only=True)
    formatted_duration = serializers.CharField(read_only=True)
    stream_url = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'artist_name', 'artist_id', 'album_title',
            'album_id', 'album_cover', 'genre_name', 'genre', 'duration',
            'formatted_duration', 'release_date', 'track_number', 'disc_number',
            'explicit', 'lyrics', 'play_count', 'like_count', 'bitrate',
            'is_available', 'stream_url', 'created_at'
        ]

    def get_stream_url(self, obj):
        return f'/api/v1/stream/{obj.id}/'


class TrackCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating tracks.
    """
    duration = serializers.DurationField()

    class Meta:
        model = Track
        fields = [
            'title', 'artist', 'album', 'duration', 'release_date',
            'genre', 'audio_file', 'track_number', 'disc_number',
            'explicit', 'lyrics', 'is_available'
        ]

    def validate_audio_file(self, value):
        """Validate audio file size."""
        max_size = 100 * 1024 * 1024  # 100 MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f'Audio file size cannot exceed {max_size // (1024*1024)} MB.'
            )
        return value


class TrackSerializer(serializers.ModelSerializer):
    """
    Legacy serializer for backward compatibility.
    """
    artist = serializers.CharField(source='artist.name', read_only=True)
    album = serializers.CharField(source='album.title', read_only=True)
    genre = serializers.CharField(source='genre.name', read_only=True)

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'artist', 'album', 'duration',
            'release_date', 'genre', 'audio_file', 'play_count'
        ]


class UserSerializer(serializers.ModelSerializer):
    """User serializer for authentication."""
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email']
        extra_kwargs = {'password': {'write_only': True}}


class ArtistSerializer(serializers.ModelSerializer):
    """Artist serializer."""
    class Meta:
        model = Artist
        fields = ['id', 'name', 'biography', 'genres']


class AlbumSerializer(serializers.ModelSerializer):
    """Album serializer."""
    class Meta:
        model = Album
        fields = ['id', 'title', 'artist', 'release_date', 'cover_art']
