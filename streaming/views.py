"""
Audio streaming views with HTTP Range request support.

This module provides endpoints for streaming audio files with:
- HTTP Range requests for seeking and partial content
- Chunked transfer encoding
- Proper MIME type detection
- Play count tracking
- Stream quality selection
"""

import os
import re
import mimetypes
import logging
from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from music.models import Track
from .models import PlayHistory, StreamSession
from core.exceptions import StreamingError, NotFoundError

logger = logging.getLogger('streaming')


class StreamingThrottle(UserRateThrottle):
    """Custom throttle for streaming endpoints."""
    scope = 'streaming'


def get_content_type(file_path):
    """Get the MIME type for an audio file."""
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        # Default to octet-stream for unknown types
        content_type = 'application/octet-stream'
    return content_type


def parse_range_header(range_header, file_size):
    """
    Parse HTTP Range header and return start and end positions.

    Supports formats:
    - bytes=0-499 (first 500 bytes)
    - bytes=500-999 (second 500 bytes)
    - bytes=-500 (last 500 bytes)
    - bytes=500- (from byte 500 to end)
    """
    if not range_header:
        return 0, file_size - 1

    range_match = re.match(r'bytes=(\d*)-(\d*)', range_header)
    if not range_match:
        return 0, file_size - 1

    start_str, end_str = range_match.groups()

    if start_str and end_str:
        start = int(start_str)
        end = min(int(end_str), file_size - 1)
    elif start_str:
        start = int(start_str)
        end = file_size - 1
    elif end_str:
        # Last N bytes
        start = max(0, file_size - int(end_str))
        end = file_size - 1
    else:
        start = 0
        end = file_size - 1

    return start, end


def file_iterator(file_path, start=0, end=None, chunk_size=None):
    """
    Generator that yields file chunks for streaming.

    Args:
        file_path: Path to the file
        start: Start byte position
        end: End byte position (inclusive)
        chunk_size: Size of each chunk in bytes
    """
    if chunk_size is None:
        chunk_size = getattr(settings, 'STREAMING_CHUNK_SIZE', 256 * 1024)

    with open(file_path, 'rb') as f:
        f.seek(start)
        remaining = (end - start + 1) if end else None

        while True:
            if remaining is not None:
                chunk_size = min(chunk_size, remaining)
                if chunk_size <= 0:
                    break

            data = f.read(chunk_size)
            if not data:
                break

            if remaining is not None:
                remaining -= len(data)

            yield data


@extend_schema(
    summary="Stream audio track",
    description="Stream an audio track with HTTP Range request support for seeking.",
    parameters=[
        OpenApiParameter(
            name='track_id',
            type=int,
            location=OpenApiParameter.PATH,
            description='ID of the track to stream'
        ),
        OpenApiParameter(
            name='quality',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Stream quality: low, medium, high, lossless',
            required=False
        ),
    ],
    responses={
        200: OpenApiResponse(description='Full audio file'),
        206: OpenApiResponse(description='Partial audio content'),
        404: OpenApiResponse(description='Track not found'),
        416: OpenApiResponse(description='Range not satisfiable'),
    },
    tags=['Streaming']
)
@api_view(['GET', 'HEAD'])
@permission_classes([IsAuthenticated])
@throttle_classes([StreamingThrottle])
def stream_track(request, track_id):
    """
    Stream an audio track with HTTP Range request support.

    Supports:
    - Partial content requests (206) for seeking
    - HEAD requests for metadata
    - Play history tracking
    """
    # Get the track
    track = get_object_or_404(Track, id=track_id)

    # Check if audio file exists
    if not track.audio_file:
        raise NotFoundError('Audio file not available for this track.')

    file_path = track.audio_file.path

    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        raise NotFoundError('Audio file not found on server.')

    file_size = os.path.getsize(file_path)
    content_type = get_content_type(file_path)

    # Parse Range header
    range_header = request.META.get('HTTP_RANGE')
    start, end = parse_range_header(range_header, file_size)

    # Validate range
    if start >= file_size:
        return HttpResponse(
            status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={'Content-Range': f'bytes */{file_size}'}
        )

    # Calculate content length for this chunk
    content_length = end - start + 1

    # HEAD request - return metadata only
    if request.method == 'HEAD':
        response = HttpResponse(content_type=content_type)
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = file_size
        return response

    # Track play history (only on start of stream)
    if start == 0:
        try:
            PlayHistory.objects.create(
                user=request.user,
                track=track,
            )
            # Increment play count
            Track.objects.filter(id=track_id).update(
                play_count=models.F('play_count') + 1
            )
        except Exception as e:
            logger.warning(f"Failed to record play history: {e}")

    # Create streaming response
    if range_header:
        # Partial content response
        response = StreamingHttpResponse(
            file_iterator(file_path, start, end),
            status=status.HTTP_206_PARTIAL_CONTENT,
            content_type=content_type
        )
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    else:
        # Full content response
        response = StreamingHttpResponse(
            file_iterator(file_path, 0, file_size - 1),
            content_type=content_type
        )

    response['Content-Length'] = content_length
    response['Accept-Ranges'] = 'bytes'
    response['Cache-Control'] = 'no-cache'

    logger.info(
        f"Streaming track {track_id} to user {request.user.id}",
        extra={
            'track_id': track_id,
            'user_id': request.user.id,
            'range': f'{start}-{end}',
            'content_length': content_length,
        }
    )

    return response


@extend_schema(
    summary="Get track stream URL",
    description="Get a temporary streaming URL for a track.",
    tags=['Streaming']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stream_url(request, track_id):
    """
    Get streaming information for a track.
    Returns metadata needed by the client to initiate streaming.
    """
    track = get_object_or_404(Track, id=track_id)

    if not track.audio_file:
        raise NotFoundError('Audio file not available for this track.')

    file_path = track.audio_file.path
    if not os.path.exists(file_path):
        raise NotFoundError('Audio file not found on server.')

    file_size = os.path.getsize(file_path)
    content_type = get_content_type(file_path)

    # Get available quality options
    quality_options = getattr(settings, 'STREAMING_QUALITY_PRESETS', {})

    return Response({
        'track_id': track.id,
        'stream_url': f'/api/v1/stream/{track.id}/',
        'file_size': file_size,
        'content_type': content_type,
        'duration': str(track.duration) if track.duration else None,
        'quality_options': list(quality_options.keys()),
    })


@extend_schema(
    summary="Get user's play history",
    description="Get the authenticated user's recently played tracks.",
    tags=['Streaming']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_play_history(request):
    """Get the user's play history with pagination."""
    from rest_framework.pagination import PageNumberPagination
    from music.serializers import TrackSerializer

    history = PlayHistory.objects.filter(
        user=request.user
    ).select_related('track', 'track__artist', 'track__album').order_by('-played_at')

    paginator = PageNumberPagination()
    paginator.page_size = 50
    page = paginator.paginate_queryset(history, request)

    data = []
    for entry in page:
        track_data = TrackSerializer(entry.track).data
        track_data['played_at'] = entry.played_at.isoformat()
        data.append(track_data)

    return paginator.get_paginated_response(data)


@extend_schema(
    summary="Clear play history",
    description="Clear the authenticated user's play history.",
    tags=['Streaming']
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_play_history(request):
    """Clear user's play history."""
    deleted_count, _ = PlayHistory.objects.filter(user=request.user).delete()
    return Response({
        'message': f'Cleared {deleted_count} history entries.'
    })


# Import models at runtime to avoid circular imports
from django.db import models
