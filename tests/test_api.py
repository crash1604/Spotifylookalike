"""
Integration tests for API endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories import (
    UserFactory,
    GenreFactory,
    ArtistFactory,
    AlbumFactory,
    TrackFactory,
    PlaylistFactory,
)


# =============================================================================
# Authentication Tests
# =============================================================================

@pytest.mark.django_db
class TestAuthentication:
    """Tests for authentication endpoints."""

    def test_obtain_token(self, api_client):
        """Test obtaining JWT tokens."""
        user = UserFactory()
        response = api_client.post('/api/v1/auth/token/', {
            'username': user.username,
            'password': 'testpass123'
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_obtain_token_invalid_credentials(self, api_client):
        """Test token request with invalid credentials."""
        response = api_client.post('/api/v1/auth/token/', {
            'username': 'invalid',
            'password': 'invalid'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client):
        """Test refreshing access token."""
        user = UserFactory()
        token_response = api_client.post('/api/v1/auth/token/', {
            'username': user.username,
            'password': 'testpass123'
        })
        refresh_token = token_response.data['refresh']

        response = api_client.post('/api/v1/auth/token/refresh/', {
            'refresh': refresh_token
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_protected_endpoint_without_token(self, api_client, track):
        """Test accessing protected endpoint without token."""
        response = api_client.get('/api/v1/tracks/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Track API Tests
# =============================================================================

@pytest.mark.django_db
class TestTrackAPI:
    """Tests for Track API endpoints."""

    def test_list_tracks(self, authenticated_client, tracks):
        """Test listing all tracks."""
        response = authenticated_client.get('/api/v1/tracks/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) > 0

    def test_list_tracks_pagination(self, authenticated_client, large_dataset):
        """Test track listing pagination."""
        response = authenticated_client.get('/api/v1/tracks/?page_size=10')
        assert response.status_code == status.HTTP_200_OK
        assert 'next' in response.data
        assert len(response.data['results']) <= 10

    def test_retrieve_track(self, authenticated_client, track):
        """Test retrieving a single track."""
        response = authenticated_client.get(f'/api/v1/tracks/{track.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == track.title

    def test_search_tracks(self, authenticated_client, tracks):
        """Test searching tracks."""
        track = tracks[0]
        response = authenticated_client.get(f'/api/v1/tracks/?search={track.title}')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_tracks_by_genre(self, authenticated_client, tracks, genre):
        """Test filtering tracks by genre."""
        response = authenticated_client.get(f'/api/v1/tracks/?genre={genre.id}')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_tracks_by_artist(self, authenticated_client, tracks, artist):
        """Test filtering tracks by artist."""
        response = authenticated_client.get(f'/api/v1/tracks/?artist={artist.id}')
        assert response.status_code == status.HTTP_200_OK

    def test_create_track_as_admin(self, admin_client, artist, album, genre):
        """Test creating a track as admin."""
        data = {
            'title': 'New Track',
            'artist': artist.id,
            'album': album.id,
            'genre': genre.id,
            'duration': '00:03:30',
            'release_date': '2024-01-15'
        }
        response = admin_client.post('/api/v1/tracks/', data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_track_as_regular_user(self, authenticated_client, artist, album, genre):
        """Test that regular users cannot create tracks."""
        data = {
            'title': 'New Track',
            'artist': artist.id,
            'album': album.id,
            'genre': genre.id,
            'duration': '00:03:30',
            'release_date': '2024-01-15'
        }
        response = authenticated_client.post('/api/v1/tracks/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_top_tracks(self, authenticated_client, tracks):
        """Test getting top tracks."""
        response = authenticated_client.get('/api/v1/tracks/top/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_recent_tracks(self, authenticated_client, tracks):
        """Test getting recent tracks."""
        response = authenticated_client.get('/api/v1/tracks/recent/')
        assert response.status_code == status.HTTP_200_OK

    def test_increment_play_count(self, authenticated_client, track):
        """Test incrementing play count."""
        initial_count = track.play_count
        response = authenticated_client.post(f'/api/v1/tracks/{track.id}/play/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['play_count'] == initial_count + 1


# =============================================================================
# Artist API Tests
# =============================================================================

@pytest.mark.django_db
class TestArtistAPI:
    """Tests for Artist API endpoints."""

    def test_list_artists(self, authenticated_client, artists):
        """Test listing all artists."""
        response = authenticated_client.get('/api/v1/artists/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_retrieve_artist(self, authenticated_client, artist):
        """Test retrieving a single artist."""
        response = authenticated_client.get(f'/api/v1/artists/{artist.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == artist.name

    def test_search_artists(self, authenticated_client, artists):
        """Test searching artists."""
        artist = artists[0]
        response = authenticated_client.get(f'/api/v1/artists/?search={artist.name}')
        assert response.status_code == status.HTTP_200_OK

    def test_get_artist_albums(self, authenticated_client, artist, albums):
        """Test getting artist's albums."""
        response = authenticated_client.get(f'/api/v1/artists/{artist.id}/albums/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_artist_tracks(self, authenticated_client, artist, tracks):
        """Test getting artist's tracks."""
        response = authenticated_client.get(f'/api/v1/artists/{artist.id}/tracks/')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Album API Tests
# =============================================================================

@pytest.mark.django_db
class TestAlbumAPI:
    """Tests for Album API endpoints."""

    def test_list_albums(self, authenticated_client, albums):
        """Test listing all albums."""
        response = authenticated_client.get('/api/v1/albums/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_retrieve_album(self, authenticated_client, album):
        """Test retrieving a single album."""
        response = authenticated_client.get(f'/api/v1/albums/{album.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == album.title

    def test_filter_albums_by_artist(self, authenticated_client, albums, artist):
        """Test filtering albums by artist."""
        response = authenticated_client.get(f'/api/v1/albums/?artist={artist.id}')
        assert response.status_code == status.HTTP_200_OK

    def test_get_album_tracks(self, authenticated_client, album, tracks):
        """Test getting album's tracks."""
        response = authenticated_client.get(f'/api/v1/albums/{album.id}/tracks/')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Playlist API Tests
# =============================================================================

@pytest.mark.django_db
class TestPlaylistAPI:
    """Tests for Playlist API endpoints."""

    def test_list_playlists(self, authenticated_client, playlists):
        """Test listing playlists."""
        response = authenticated_client.get('/api/v1/playlists/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_playlist(self, authenticated_client):
        """Test creating a playlist."""
        data = {
            'title': 'My New Playlist',
            'description': 'A test playlist',
            'is_public': True
        }
        response = authenticated_client.post('/api/v1/playlists/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'My New Playlist'

    def test_retrieve_playlist(self, authenticated_client, playlist):
        """Test retrieving a playlist."""
        response = authenticated_client.get(f'/api/v1/playlists/{playlist.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_update_own_playlist(self, authenticated_client, user, tracks):
        """Test updating own playlist."""
        playlist = PlaylistFactory(owner=user)
        data = {'title': 'Updated Title'}
        response = authenticated_client.patch(f'/api/v1/playlists/{playlist.id}/', data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'

    def test_delete_own_playlist(self, authenticated_client, user):
        """Test deleting own playlist."""
        playlist = PlaylistFactory(owner=user)
        response = authenticated_client.delete(f'/api/v1/playlists/{playlist.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_update_others_playlist(self, authenticated_client, playlist):
        """Test that users cannot update others' playlists."""
        other_user = UserFactory()
        other_playlist = PlaylistFactory(owner=other_user)
        data = {'title': 'Hacked Title'}
        response = authenticated_client.patch(f'/api/v1/playlists/{other_playlist.id}/', data)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_add_tracks_to_playlist(self, authenticated_client, user, tracks):
        """Test adding tracks to playlist."""
        playlist = PlaylistFactory(owner=user)
        data = {'track_ids': [tracks[0].id, tracks[1].id]}
        response = authenticated_client.post(f'/api/v1/playlists/{playlist.id}/add_tracks/', data)
        assert response.status_code == status.HTTP_200_OK

    def test_remove_tracks_from_playlist(self, authenticated_client, user, tracks):
        """Test removing tracks from playlist."""
        playlist = PlaylistFactory(owner=user)
        playlist.track_list.add(*tracks[:3])
        data = {'track_ids': [tracks[0].id]}
        response = authenticated_client.post(f'/api/v1/playlists/{playlist.id}/remove_tracks/', data)
        assert response.status_code == status.HTTP_200_OK

    def test_get_my_playlists(self, authenticated_client, user):
        """Test getting current user's playlists."""
        PlaylistFactory.create_batch(3, owner=user)
        response = authenticated_client.get('/api/v1/playlists/mine/')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Genre API Tests
# =============================================================================

@pytest.mark.django_db
class TestGenreAPI:
    """Tests for Genre API endpoints."""

    def test_list_genres(self, authenticated_client, genres):
        """Test listing all genres."""
        response = authenticated_client.get('/api/v1/genres/')
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_genre(self, authenticated_client, genre):
        """Test retrieving a single genre."""
        response = authenticated_client.get(f'/api/v1/genres/{genre.slug}/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_genre_tracks(self, authenticated_client, genre, tracks):
        """Test getting tracks by genre."""
        response = authenticated_client.get(f'/api/v1/genres/{genre.slug}/tracks/')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Streaming API Tests
# =============================================================================

@pytest.mark.django_db
class TestStreamingAPI:
    """Tests for Streaming API endpoints."""

    def test_get_play_history(self, authenticated_client, user):
        """Test getting play history."""
        from tests.factories import PlayHistoryFactory
        PlayHistoryFactory.create_batch(5, user=user)
        response = authenticated_client.get('/api/v1/stream/history/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_favorites(self, authenticated_client, user, tracks):
        """Test getting user favorites."""
        from tests.factories import UserFavoriteFactory
        UserFavoriteFactory.create_batch(3, user=user)
        response = authenticated_client.get('/api/v1/stream/favorites/')
        assert response.status_code == status.HTTP_200_OK

    def test_add_favorite(self, authenticated_client, track):
        """Test adding a track to favorites."""
        data = {'track_id': track.id}
        response = authenticated_client.post('/api/v1/stream/favorites/', data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_remove_favorite(self, authenticated_client, user, track):
        """Test removing a track from favorites."""
        from tests.factories import UserFavoriteFactory
        UserFavoriteFactory(user=user, track=track)
        response = authenticated_client.delete(f'/api/v1/stream/favorites/{track.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# Health Check Tests
# =============================================================================

@pytest.mark.django_db
class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, api_client):
        """Test health check endpoint."""
        response = api_client.get('/health/')
        assert response.status_code == status.HTTP_200_OK
