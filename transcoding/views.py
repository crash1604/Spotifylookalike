"""
API views for the transcoding service.
"""

import logging
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from music.models import Track
from .models import TranscodedTrack
from .serializers import TranscodedTrackSerializer, TranscodeRequestSerializer
from .tasks import transcode_track, transcode_all_qualities, generate_waveform_task

logger = logging.getLogger('transcoding')


@extend_schema(
    summary='List transcoded variants for a track',
    tags=['Transcoding'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_variants(request, track_id):
    """Return every transcoded variant available for a track."""
    get_object_or_404(Track, id=track_id)
    variants = TranscodedTrack.objects.filter(
        original_track_id=track_id,
        status='completed',
    )
    serializer = TranscodedTrackSerializer(variants, many=True)
    return Response(serializer.data)


@extend_schema(
    summary='Trigger transcoding for a track',
    request=TranscodeRequestSerializer,
    tags=['Transcoding'],
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_transcode(request, track_id):
    """
    Queue a transcoding job for a single quality level.
    Admin-only.
    """
    track = get_object_or_404(Track, id=track_id)
    ser = TranscodeRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    quality = ser.validated_data['quality']
    transcode_track.delay(track.id, quality)

    return Response(
        {'message': f'Transcoding queued for track {track.id} at {quality}.'},
        status=status.HTTP_202_ACCEPTED,
    )


@extend_schema(
    summary='Trigger transcoding for all quality presets',
    tags=['Transcoding'],
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_transcode_all(request, track_id):
    """
    Queue transcoding jobs for *every* quality preset.
    Admin-only.
    """
    track = get_object_or_404(Track, id=track_id)
    transcode_all_qualities.delay(track.id)

    return Response(
        {'message': f'Transcoding queued for all quality presets of track {track.id}.'},
        status=status.HTTP_202_ACCEPTED,
    )


@extend_schema(
    summary='Generate waveform data for a track',
    tags=['Transcoding'],
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_waveform(request, track_id):
    """Queue waveform generation for a track. Admin-only."""
    track = get_object_or_404(Track, id=track_id)
    generate_waveform_task.delay(track.id)
    return Response(
        {'message': f'Waveform generation queued for track {track.id}.'},
        status=status.HTTP_202_ACCEPTED,
    )
