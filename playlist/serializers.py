"""
Serializers for playlist-related models.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Playlist
from music.models import Track


class PlaylistListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for playlist listings."""
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    track_count = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ['id', 'title', 'owner_name', 'cover_art', 'is_public', 'track_count', 'updated_at']

    def get_track_count(self, obj):
        return obj.track_list.count()


class PlaylistDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual playlist view."""
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    track_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    tracks = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = [
            'id', 'title', 'description', 'owner', 'owner_name',
            'cover_art', 'is_public', 'track_count', 'total_duration',
            'tracks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['owner']

    def get_track_count(self, obj):
        return obj.track_list.count()

    def get_total_duration(self, obj):
        from django.db.models import Sum
        total = obj.track_list.aggregate(total=Sum('duration'))['total']
        if total:
            total_seconds = int(total.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            return f"{minutes}:{seconds:02d}"
        return "0:00"

    def get_tracks(self, obj):
        from music.serializers import TrackListSerializer
        tracks = obj.track_list.filter(is_available=True)[:50]
        return TrackListSerializer(tracks, many=True).data


class PlaylistSerializer(serializers.ModelSerializer):
    """Legacy serializer for backward compatibility."""
    track_list = serializers.PrimaryKeyRelatedField(
        queryset=Track.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Playlist
        fields = ['id', 'title', 'description', 'creation_date', 'owner', 'cover_art', 'track_list', 'is_public']
        read_only_fields = ['owner']
