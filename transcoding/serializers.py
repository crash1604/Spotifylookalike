"""
Serializers for the transcoding app.
"""

from rest_framework import serializers
from .models import TranscodedTrack


class TranscodedTrackSerializer(serializers.ModelSerializer):
    """Read-only representation of a transcoded variant."""
    stream_url = serializers.SerializerMethodField()

    class Meta:
        model = TranscodedTrack
        fields = [
            'id', 'quality', 'codec', 'bitrate', 'sample_rate',
            'file_size', 'status', 'stream_url', 'created_at', 'completed_at',
        ]

    def get_stream_url(self, obj):
        if obj.status == 'completed' and obj.file:
            track_id = obj.original_track_id
            return f'/api/v1/stream/{track_id}/?quality={obj.quality}'
        return None


class TranscodeRequestSerializer(serializers.Serializer):
    """Validate an incoming transcode request."""
    quality = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'lossless'],
        default='medium',
    )
