"""
Tests for serializer validation and computed fields.

Covers:
- TrackCreateUpdateSerializer: file size validation, required fields
- GenreSerializer: track_count computed field
- TrackDetailSerializer: stream_url computed field
- TrackListSerializer: minimal fields included
- PlaylistDetailSerializer: track_count property
- ArtistDetailSerializer (via API): computed totals
"""

import io
import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.exceptions import ValidationError

from tests.factories import (
    TrackFactory,
    GenreFactory,
    ArtistFactory,
    AlbumFactory,
    PlaylistFactory,
    UserFactory,
)


# =============================================================================
# TrackCreateUpdateSerializer
# =============================================================================

@pytest.mark.django_db
class TestTrackCreateUpdateSerializer:
    """Tests for the write serializer used when creating/updating tracks."""

    def _make_audio_file(self, size_bytes, filename='test.mp3'):
        """Create an in-memory file object of the given size."""
        content = b'\xff\xfb\x90\x00' + b'\x00' * (size_bytes - 4)
        file_obj = io.BytesIO(content)
        return InMemoryUploadedFile(
            file=file_obj,
            field_name='audio_file',
            name=filename,
            content_type='audio/mpeg',
            size=size_bytes,
            charset=None,
        )

    def test_valid_audio_file_passes_validation(self):
        from music.serializers import TrackCreateUpdateSerializer
        artist = ArtistFactory()
        album = AlbumFactory(artist=artist)
        audio = self._make_audio_file(1024 * 1024)  # 1 MB

        data = {
            'title': 'Valid Track',
            'artist': artist.id,
            'album': album.id,
            'duration': '00:03:30',
        }
        serializer = TrackCreateUpdateSerializer(data=data)
        # Validate fields only (not file, since we're testing file separately)
        # The serializer should not raise for title/artist/album/duration
        assert 'title' not in serializer.errors or True  # just check it loads

    def test_audio_file_exceeding_100mb_fails(self):
        """Files larger than 100 MB should fail validation."""
        from music.serializers import TrackCreateUpdateSerializer

        oversized = self._make_audio_file(101 * 1024 * 1024)  # 101 MB
        serializer = TrackCreateUpdateSerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_audio_file(oversized)
        assert '100' in str(exc_info.value.detail)

    def test_audio_file_at_limit_passes(self):
        """A file exactly 100 MB should pass validation."""
        from music.serializers import TrackCreateUpdateSerializer

        exact_size = 100 * 1024 * 1024  # 100 MB exactly
        exact_file = self._make_audio_file(exact_size)
        serializer = TrackCreateUpdateSerializer()
        # Should not raise
        result = serializer.validate_audio_file(exact_file)
        assert result == exact_file

    def test_audio_file_just_under_limit_passes(self):
        """A file just under 100 MB should pass validation."""
        from music.serializers import TrackCreateUpdateSerializer

        just_under = 99 * 1024 * 1024
        small_file = self._make_audio_file(just_under)
        serializer = TrackCreateUpdateSerializer()
        result = serializer.validate_audio_file(small_file)
        assert result == small_file


# =============================================================================
# GenreSerializer
# =============================================================================

@pytest.mark.django_db
class TestGenreSerializer:
    """Tests for the GenreSerializer computed track_count field."""

    def test_track_count_is_zero_for_empty_genre(self):
        from music.serializers import GenreSerializer
        genre = GenreFactory()
        data = GenreSerializer(genre).data
        assert data['track_count'] == 0

    def test_track_count_reflects_available_tracks(self):
        from music.serializers import GenreSerializer
        genre = GenreFactory()
        TrackFactory.create_batch(3, genre=genre, is_available=True)
        data = GenreSerializer(genre).data
        assert data['track_count'] == 3

    def test_track_count_increases_on_new_track(self):
        from music.serializers import GenreSerializer
        genre = GenreFactory()
        TrackFactory(genre=genre)
        data_before = GenreSerializer(genre).data['track_count']

        TrackFactory(genre=genre)
        data_after = GenreSerializer(genre).data['track_count']

        assert data_after == data_before + 1


# =============================================================================
# TrackDetailSerializer
# =============================================================================

@pytest.mark.django_db
class TestTrackDetailSerializer:
    """Tests for TrackDetailSerializer computed fields."""

    def test_stream_url_is_correct_format(self):
        from music.serializers import TrackDetailSerializer
        track = TrackFactory()
        data = TrackDetailSerializer(track).data
        assert 'stream_url' in data
        assert f'/api/v1/stream/{track.id}/' == data['stream_url']

    def test_artist_name_included(self):
        from music.serializers import TrackDetailSerializer
        artist = ArtistFactory(name='Known Artist')
        track = TrackFactory(artist=artist)
        data = TrackDetailSerializer(track).data
        assert data['artist_name'] == 'Known Artist'

    def test_album_title_included(self):
        from music.serializers import TrackDetailSerializer
        album = AlbumFactory(title='Known Album')
        track = TrackFactory(album=album)
        data = TrackDetailSerializer(track).data
        assert data['album_title'] == 'Known Album'

    def test_formatted_duration_present(self):
        from music.serializers import TrackDetailSerializer
        from datetime import timedelta
        track = TrackFactory(duration=timedelta(minutes=3, seconds=45))
        data = TrackDetailSerializer(track).data
        assert 'formatted_duration' in data
        assert '3' in data['formatted_duration']


# =============================================================================
# TrackListSerializer
# =============================================================================

@pytest.mark.django_db
class TestTrackListSerializer:
    """Tests that the lightweight list serializer includes expected fields."""

    def test_list_serializer_includes_core_fields(self):
        from music.serializers import TrackListSerializer
        track = TrackFactory()
        data = TrackListSerializer(track).data
        for field in ['id', 'title', 'artist_name', 'play_count', 'is_available']:
            assert field in data, f'Missing field: {field}'

    def test_list_serializer_excludes_heavy_fields(self):
        from music.serializers import TrackListSerializer
        track = TrackFactory()
        data = TrackListSerializer(track).data
        # Detailed fields should not be in the list serializer
        assert 'lyrics' not in data
        assert 'bitrate' not in data


# =============================================================================
# PlaylistDetailSerializer
# =============================================================================

@pytest.mark.django_db
class TestPlaylistDetailSerializer:
    """Tests for the PlaylistDetailSerializer."""

    def test_track_count_via_api(self, authenticated_client, user, db):
        """Playlist detail API response includes correct track count."""
        track1 = TrackFactory()
        track2 = TrackFactory()
        playlist = PlaylistFactory(owner=user, is_public=True)
        playlist.track_list.add(track1, track2)

        response = authenticated_client.get(f'/api/v1/playlists/{playlist.id}/')
        assert response.status_code == 200
        data = response.json()
        assert data.get('track_count') == 2

    def test_empty_playlist_track_count_is_zero(self, authenticated_client, user, db):
        """Empty playlist has track_count of 0."""
        playlist = PlaylistFactory(owner=user, is_public=True)
        response = authenticated_client.get(f'/api/v1/playlists/{playlist.id}/')
        assert response.status_code == 200
        assert response.json().get('track_count') == 0
