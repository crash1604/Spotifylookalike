"""
Pytest configuration and fixtures for the music streaming API tests.
"""

import pytest
from unittest.mock import MagicMock, patch
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

from tests.factories import (
    UserFactory,
    GenreFactory,
    ArtistFactory,
    AlbumFactory,
    TrackFactory,
    PlaylistFactory,
    TranscodedTrackFactory,
    StreamSessionFactory,
)


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return UserFactory()


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    user = UserFactory(is_staff=True, is_superuser=True)
    return user


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an authenticated admin API client."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


# =============================================================================
# Music Data Fixtures
# =============================================================================

@pytest.fixture
def genre(db):
    """Create and return a test genre."""
    return GenreFactory(name='Rock', slug='rock')


@pytest.fixture
def genres(db):
    """Create and return multiple test genres."""
    return [
        GenreFactory(name='Rock', slug='rock'),
        GenreFactory(name='Pop', slug='pop'),
        GenreFactory(name='Jazz', slug='jazz'),
        GenreFactory(name='Electronic', slug='electronic'),
        GenreFactory(name='Hip Hop', slug='hip-hop'),
    ]


@pytest.fixture
def artist(db, genre):
    """Create and return a test artist."""
    artist = ArtistFactory(name='Test Artist')
    artist.genres.add(genre)
    return artist


@pytest.fixture
def artists(db, genres):
    """Create and return multiple test artists."""
    artists_list = []
    for i, g in enumerate(genres):
        artist = ArtistFactory(name=f'Artist {i}')
        artist.genres.add(g)
        artists_list.append(artist)
    return artists_list


@pytest.fixture
def album(db, artist):
    """Create and return a test album."""
    return AlbumFactory(artist=artist, title='Test Album')


@pytest.fixture
def albums(db, artists):
    """Create and return multiple test albums."""
    albums_list = []
    for artist in artists:
        for i in range(2):
            albums_list.append(AlbumFactory(artist=artist))
    return albums_list


@pytest.fixture
def track(db, artist, album, genre):
    """Create and return a test track."""
    return TrackFactory(
        title='Test Track',
        artist=artist,
        album=album,
        genre=genre
    )


@pytest.fixture
def tracks(db, albums, genres):
    """Create and return multiple test tracks."""
    tracks_list = []
    for album in albums:
        for i in range(5):
            genre = genres[i % len(genres)]
            tracks_list.append(TrackFactory(
                artist=album.artist,
                album=album,
                genre=genre
            ))
    return tracks_list


@pytest.fixture
def playlist(db, user, tracks):
    """Create and return a test playlist."""
    playlist = PlaylistFactory(owner=user, is_public=True)
    playlist.track_list.add(*tracks[:5])
    return playlist


@pytest.fixture
def playlists(db, user, tracks):
    """Create and return multiple test playlists."""
    playlists_list = []
    for i in range(3):
        playlist = PlaylistFactory(owner=user, is_public=i % 2 == 0)
        playlist.track_list.add(*tracks[i*3:(i+1)*3])
        playlists_list.append(playlist)
    return playlists_list


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def sample_audio_file(tmp_path):
    """Create a sample audio file for testing."""
    audio_file = tmp_path / "test_audio.mp3"
    # Create a minimal MP3-like file header
    audio_file.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * 1000)
    return audio_file


@pytest.fixture
def large_dataset(db, genres):
    """Create a large dataset for performance testing."""
    artists = [ArtistFactory() for _ in range(10)]
    for artist in artists:
        artist.genres.add(genres[0])

    albums = []
    for artist in artists:
        for _ in range(5):
            albums.append(AlbumFactory(artist=artist))

    tracks = []
    for album in albums:
        for i in range(10):
            tracks.append(TrackFactory(
                artist=album.artist,
                album=album,
                genre=genres[i % len(genres)]
            ))

    return {
        'artists': artists,
        'albums': albums,
        'tracks': tracks,
        'genres': genres
    }


# =============================================================================
# Mock Fixtures for External Services
# =============================================================================

@pytest.fixture
def mock_ffmpeg():
    """Patch subprocess.run to simulate FFmpeg execution without actual FFmpeg."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ''
    mock_result.stderr = ''
    with patch('transcoding.service.subprocess.run', return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_ffprobe():
    """Patch ffprobe subprocess to return fake audio metadata."""
    import json
    fake_metadata = {
        'format': {'duration': '210.5', 'bit_rate': '320000', 'size': '8400000'},
        'streams': [{
            'codec_type': 'audio',
            'codec_name': 'mp3',
            'sample_rate': '44100',
            'channels': 2,
            'bit_rate': '320000',
        }],
    }
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(fake_metadata)
    mock_result.stderr = ''
    with patch('transcoding.service.subprocess.run', return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_elasticsearch(monkeypatch):
    """Patch Elasticsearch DSL search to avoid needing a real ES instance."""
    mock_hit = MagicMock()
    mock_hit.meta.id = '1'
    mock_hit.meta.score = 1.0

    mock_response = MagicMock()
    mock_response.__iter__ = MagicMock(return_value=iter([mock_hit]))

    mock_search = MagicMock()
    mock_search.query.return_value = mock_search
    mock_search.filter.return_value = mock_search
    mock_search.__getitem__ = MagicMock(return_value=mock_search)
    mock_search.execute.return_value = mock_response

    monkeypatch.setattr('search.documents.TrackDocument.search', lambda: mock_search)
    monkeypatch.setattr('search.documents.ArtistDocument.search', lambda: mock_search)
    monkeypatch.setattr('search.documents.AlbumDocument.search', lambda: mock_search)
    return mock_search


@pytest.fixture
def other_user(db):
    """A second user – useful for testing ownership/isolation."""
    return UserFactory(username='other_user')
