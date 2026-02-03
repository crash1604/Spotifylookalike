"""
Serializers for album-related models.
"""

from rest_framework import serializers
from .models import Album


class AlbumListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for album listings."""
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    track_count = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = ['id', 'title', 'artist_name', 'release_date', 'cover_art', 'track_count']

    def get_track_count(self, obj):
        return obj.tracks.count()


class AlbumDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual album view."""
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_id = serializers.IntegerField(source='artist.id', read_only=True)
    track_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    total_plays = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = [
            'id', 'title', 'artist', 'artist_name', 'artist_id',
            'release_date', 'cover_art', 'track_count', 'total_duration',
            'total_plays', 'created_at'
        ]

    def get_track_count(self, obj):
        return obj.tracks.count()

    def get_total_duration(self, obj):
        from django.db.models import Sum
        total = obj.tracks.aggregate(total=Sum('duration'))['total']
        if total:
            total_seconds = int(total.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            return f"{minutes}:{seconds:02d}"
        return "0:00"

    def get_total_plays(self, obj):
        from django.db.models import Sum
        return obj.tracks.aggregate(total=Sum('play_count'))['total'] or 0


class AlbumSerializer(serializers.ModelSerializer):
    """Legacy serializer for backward compatibility."""
    class Meta:
        model = Album
        fields = '__all__'
