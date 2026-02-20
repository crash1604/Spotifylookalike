"""
Tests for the audio streaming module.

Covers:
- HTTP Range request parsing (various byte-range formats)
- 206 Partial Content response with correct headers
- 416 Range Not Satisfiable for invalid ranges
- Full-file 200 response
- HEAD request metadata
- Play history recording on stream start
- Play count increment on stream start
"""

import os
import pytest
from django.urls import reverse
from django.test import override_settings
from rest_framework import status

from tests.factories import TrackFactory, UserFactory
from streaming.models import PlayHistory


# =============================================================================
# Helpers
# =============================================================================

def make_audio_file(tmp_path, size=2000):
    """Create a real audio-like file on disk for streaming tests."""
    audio = tmp_path / 'test.mp3'
    audio.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * (size - 4))
    return audio


# =============================================================================
# Range Request Parsing Unit Tests
# =============================================================================

class TestParseRangeHeader:
    """Unit tests for the parse_range_header helper function."""

    def test_full_range_parsed_correctly(self):
        from streaming.views import parse_range_header
        start, end = parse_range_header('bytes=0-499', 1000)
        assert start == 0
        assert end == 499

    def test_range_from_start(self):
        from streaming.views import parse_range_header
        start, end = parse_range_header('bytes=500-', 1000)
        assert start == 500
        assert end == 999  # file_size - 1

    def test_suffix_range(self):
        from streaming.views import parse_range_header
        start, end = parse_range_header('bytes=-100', 1000)
        assert start == 900
        assert end == 999

    def test_no_range_header_returns_full_file(self):
        from streaming.views import parse_range_header
        start, end = parse_range_header(None, 1000)
        assert start == 0
        assert end == 999

    def test_end_clamped_to_file_size(self):
        from streaming.views import parse_range_header
        start, end = parse_range_header('bytes=0-9999', 500)
        assert end == 499  # file_size - 1

    def test_malformed_range_returns_full_file(self):
        from streaming.views import parse_range_header
        start, end = parse_range_header('invalid-header', 1000)
        assert start == 0
        assert end == 999


# =============================================================================
# Streaming View Integration Tests
# =============================================================================

@pytest.mark.django_db
class TestStreamTrackView:
    """Integration tests for stream_track endpoint."""

    @pytest.fixture(autouse=True)
    def setup_track(self, authenticated_client, tmp_path, settings):
        """Create a track backed by a real temporary file."""
        settings.MEDIA_ROOT = str(tmp_path)
        self.audio_file = make_audio_file(tmp_path, size=2000)
        self.client = authenticated_client

        # Create track and point its file to the temp file
        self.track = TrackFactory()
        # Update the track to use the temp file path
        self.track.audio_file.name = str(self.audio_file.relative_to(tmp_path))
        # Save the raw file path for assertions
        self.file_size = 2000
        # Override the file path to use tmp_path
        self.track.audio_file = str(self.audio_file)

    def _stream_url(self, track_id=None):
        return f'/api/v1/stream/{track_id or self.track.id}/'

    def test_full_file_stream_returns_200(self, authenticated_client, tmp_path, settings):
        """GET without Range header returns 200 and full content."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=500)

        track = TrackFactory()
        track.audio_file.save('stream_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'Accept-Ranges' in response
        assert response['Accept-Ranges'] == 'bytes'

    def test_range_request_returns_206(self, authenticated_client, tmp_path, settings):
        """GET with Range header returns 206 Partial Content."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=1000)

        track = TrackFactory()
        track.audio_file.save('range_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        response = authenticated_client.get(url, HTTP_RANGE='bytes=0-199')

        assert response.status_code == status.HTTP_206_PARTIAL_CONTENT
        assert 'Content-Range' in response
        assert response['Content-Range'].startswith('bytes 0-199/')

    def test_range_response_has_correct_content_range_header(self, authenticated_client, tmp_path, settings):
        """Content-Range header format is bytes start-end/total."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=1000)

        track = TrackFactory()
        track.audio_file.save('hdr_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        response = authenticated_client.get(url, HTTP_RANGE='bytes=100-299')

        assert response.status_code == status.HTTP_206_PARTIAL_CONTENT
        content_range = response['Content-Range']
        assert content_range == f'bytes 100-299/1000'

    def test_invalid_range_start_beyond_eof_returns_416(self, authenticated_client, tmp_path, settings):
        """Range starting beyond file size returns 416."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=500)

        track = TrackFactory()
        track.audio_file.save('eof_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        response = authenticated_client.get(url, HTTP_RANGE='bytes=9999-99999')

        assert response.status_code == status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
        assert 'Content-Range' in response
        assert response['Content-Range'] == 'bytes */500'

    def test_head_request_returns_metadata_no_body(self, authenticated_client, tmp_path, settings):
        """HEAD request returns file metadata without body."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=750)

        track = TrackFactory()
        track.audio_file.save('head_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        response = authenticated_client.head(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'Accept-Ranges' in response
        assert 'Content-Length' in response
        assert response['Content-Length'] == '750'

    def test_nonexistent_track_returns_404(self, authenticated_client):
        """Requesting stream for non-existent track ID returns 404."""
        url = '/api/v1/stream/99999/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_access_returns_401(self, api_client, tmp_path, settings):
        """Unauthenticated users cannot access stream endpoint."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=500)

        track = TrackFactory()
        track.audio_file.save('auth_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Play History and Play Count Tests
# =============================================================================

@pytest.mark.django_db
class TestStreamPlayTracking:
    """Tests that streaming correctly records play history and increments play count."""

    def test_stream_from_start_creates_play_history(self, authenticated_client, user, tmp_path, settings):
        """Streaming from byte 0 creates a PlayHistory record."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=500)

        track = TrackFactory()
        track.audio_file.save('history_test.mp3', open(str(audio_file), 'rb'), save=True)

        history_count_before = PlayHistory.objects.filter(user=user, track=track).count()

        url = f'/api/v1/stream/{track.id}/'
        authenticated_client.get(url)

        assert PlayHistory.objects.filter(user=user, track=track).count() == history_count_before + 1

    def test_stream_from_start_increments_play_count(self, authenticated_client, tmp_path, settings):
        """Streaming from byte 0 increments the track's play count."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=500)

        track = TrackFactory(play_count=10)
        track.audio_file.save('count_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        authenticated_client.get(url)

        track.refresh_from_db()
        assert track.play_count == 11

    def test_stream_continuation_does_not_double_count(self, authenticated_client, user, tmp_path, settings):
        """Streaming from a non-zero byte offset does NOT create a new play history entry."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=1000)

        track = TrackFactory(play_count=5)
        track.audio_file.save('cont_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/{track.id}/'
        # Range continuation – not from byte 0
        authenticated_client.get(url, HTTP_RANGE='bytes=500-999')

        track.refresh_from_db()
        assert track.play_count == 5  # unchanged


# =============================================================================
# Streaming URL metadata endpoint
# =============================================================================

@pytest.mark.django_db
class TestGetStreamUrlView:
    """Tests for the stream URL / metadata endpoint."""

    def test_returns_stream_url(self, authenticated_client, tmp_path, settings):
        """GET /api/v1/stream/url/{id}/ returns stream URL and metadata."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio_file = make_audio_file(tmp_path, size=500)

        track = TrackFactory()
        track.audio_file.save('url_test.mp3', open(str(audio_file), 'rb'), save=True)

        url = f'/api/v1/stream/url/{track.id}/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'stream_url' in data
        assert str(track.id) in data['stream_url']
        assert 'file_size' in data
        assert 'content_type' in data
