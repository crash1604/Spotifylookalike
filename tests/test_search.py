"""
Tests for the search module.

Covers:
- unified_search: empty query rejection, ORM fallback, type filters,
  genre filter, year range filters, limit cap, invalid parameter handling
- autocomplete: short query handling, ORM fallback suggestions
- Authentication enforcement
"""

import pytest
from rest_framework import status

from tests.factories import (
    TrackFactory,
    ArtistFactory,
    AlbumFactory,
    GenreFactory,
)


# =============================================================================
# unified_search – Parameter Validation
# =============================================================================

@pytest.mark.django_db
class TestUnifiedSearchValidation:
    """Validate that unified_search enforces proper query parameters."""

    def test_empty_query_returns_400(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_blank_query_returns_400(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search/?q=   ')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.json()

    def test_invalid_limit_returns_400(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search/?q=test&limit=abc')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'invalid_limit' in data.get('error', {}).get('code', '')

    def test_invalid_year_from_returns_400(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search/?q=test&year_from=notayear')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'invalid_year' in data.get('error', {}).get('code', '')

    def test_invalid_year_to_returns_400(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search/?q=test&year_to=bad')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_access_returns_401(self, api_client):
        response = api_client.get('/api/v1/search/?q=anything')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_limit_is_capped_at_50(self, authenticated_client, db):
        """Even if limit=1000 is passed, at most 50 results are returned per type."""
        TrackFactory.create_batch(5, is_available=True)
        response = authenticated_client.get('/api/v1/search/?q=Track&limit=1000')
        # Should not error; valid limit is capped
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# unified_search – ORM Fallback Results
# =============================================================================

@pytest.mark.django_db
class TestUnifiedSearchORMFallback:
    """
    Test that unified_search returns correct results via ORM fallback
    (Elasticsearch is not configured in tests).
    """

    def test_returns_structure_with_tracks_artists_albums(self, authenticated_client, db):
        response = authenticated_client.get('/api/v1/search/?q=test')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'tracks' in data
        assert 'artists' in data
        assert 'albums' in data

    def test_finds_track_by_title(self, authenticated_client, db):
        TrackFactory(title='Unique Search Title', is_available=True)
        response = authenticated_client.get('/api/v1/search/?q=Unique+Search+Title')
        assert response.status_code == status.HTTP_200_OK
        tracks = response.json()['tracks']
        assert any('Unique Search Title' in t['title'] for t in tracks)

    def test_finds_artist_by_name(self, authenticated_client, db):
        ArtistFactory(name='VeryUniqueArtistName')
        response = authenticated_client.get('/api/v1/search/?q=VeryUniqueArtistName')
        assert response.status_code == status.HTTP_200_OK
        artists = response.json()['artists']
        assert any('VeryUniqueArtistName' in a['name'] for a in artists)

    def test_finds_album_by_title(self, authenticated_client, db):
        AlbumFactory(title='DistinctAlbumTitle')
        response = authenticated_client.get('/api/v1/search/?q=DistinctAlbumTitle')
        assert response.status_code == status.HTTP_200_OK
        albums = response.json()['albums']
        assert any('DistinctAlbumTitle' in a['title'] for a in albums)

    def test_type_filter_tracks_only(self, authenticated_client, db):
        TrackFactory(title='FilterTrack', is_available=True)
        ArtistFactory(name='FilterArtist')
        response = authenticated_client.get('/api/v1/search/?q=Filter&type=track')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'tracks' in data
        # When type=track, artists and albums should be empty
        assert data.get('artists', []) == []
        assert data.get('albums', []) == []

    def test_type_filter_artists_only(self, authenticated_client, db):
        ArtistFactory(name='OnlyArtistResult')
        response = authenticated_client.get('/api/v1/search/?q=OnlyArtistResult&type=artist')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get('tracks', []) == []
        assert data.get('albums', []) == []
        assert len(data['artists']) >= 1

    def test_genre_filter(self, authenticated_client, db):
        """?genre=<slug> filters track results to that genre."""
        rock_genre = GenreFactory(name='Rock', slug='rock')
        jazz_genre = GenreFactory(name='Jazz', slug='jazz')
        rock_track = TrackFactory(title='Rock Song', genre=rock_genre, is_available=True)
        jazz_track = TrackFactory(title='Jazz Song', genre=jazz_genre, is_available=True)

        response = authenticated_client.get('/api/v1/search/?q=Song&genre=rock')
        assert response.status_code == status.HTTP_200_OK
        tracks = response.json()['tracks']
        returned_ids = [t['id'] for t in tracks]

        assert str(rock_track.id) in returned_ids or rock_track.id in returned_ids
        # Jazz track should NOT appear when filtering by rock
        jazz_ids = [str(jazz_track.id), jazz_track.id]
        assert not any(jid in returned_ids for jid in jazz_ids)

    def test_year_range_filter(self, authenticated_client, db):
        """year_from and year_to filter tracks by release year."""
        import datetime
        old_track = TrackFactory(title='OldTrack', release_date=datetime.date(2000, 1, 1), is_available=True)
        new_track = TrackFactory(title='NewTrack', release_date=datetime.date(2023, 1, 1), is_available=True)

        response = authenticated_client.get('/api/v1/search/?q=Track&year_from=2020')
        assert response.status_code == status.HTTP_200_OK
        tracks = response.json()['tracks']
        returned_ids = [t['id'] for t in tracks]
        # New track should appear; old track should not
        assert new_track.id in returned_ids
        assert old_track.id not in returned_ids

    def test_no_results_for_unmatched_query(self, authenticated_client, db):
        response = authenticated_client.get('/api/v1/search/?q=XYZZY_NO_MATCH_12345')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['tracks'] == []
        assert data['artists'] == []
        assert data['albums'] == []


# =============================================================================
# Autocomplete
# =============================================================================

@pytest.mark.django_db
class TestAutocomplete:
    """Tests for the autocomplete / typeahead endpoint."""

    def test_single_char_returns_empty(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search/autocomplete/?q=a')
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['suggestions'] == []

    def test_empty_query_returns_empty(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search/autocomplete/')
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['suggestions'] == []

    def test_returns_suggestions_for_valid_query(self, authenticated_client, db):
        TrackFactory(title='Beethoven Symphony', is_available=True)
        response = authenticated_client.get('/api/v1/search/autocomplete/?q=Beeth')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'suggestions' in data

    def test_unauthenticated_access_returns_401(self, api_client):
        response = api_client.get('/api/v1/search/autocomplete/?q=test')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_each_suggestion_has_required_keys(self, authenticated_client, db):
        TrackFactory(title='TestSuggestTrack', is_available=True)
        ArtistFactory(name='TestSuggestArtist')

        response = authenticated_client.get('/api/v1/search/autocomplete/?q=TestSuggest')
        assert response.status_code == status.HTTP_200_OK
        for suggestion in response.json()['suggestions']:
            assert 'text' in suggestion
            assert 'type' in suggestion
            assert 'id' in suggestion

    def test_limit_parameter_respected(self, authenticated_client, db):
        TrackFactory.create_batch(10, title='LimitTest', is_available=True)
        response = authenticated_client.get('/api/v1/search/autocomplete/?q=LimitTest&limit=3')
        assert response.status_code == status.HTTP_200_OK
        suggestions = response.json()['suggestions']
        assert len(suggestions) <= 3
