"""
Unit tests for Django models.
"""

import pytest
from datetime import timedelta, date
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from music.models import Track, Genre
from artist.models import Artist
from album.models import Album
from playlist.models import Playlist
from streaming.models import PlayHistory, UserFavorite, UserQueue

from tests.factories import (
    UserFactory,
    GenreFactory,
    ArtistFactory,
    AlbumFactory,
    TrackFactory,
    PlaylistFactory,
    PlayHistoryFactory,
    UserFavoriteFactory,
)


# =============================================================================
# Genre Model Tests
# =============================================================================

@pytest.mark.django_db
class TestGenreModel:
    """Tests for the Genre model."""

    def test_create_genre(self):
        """Test creating a genre."""
        genre = GenreFactory(name='Rock', slug='rock')
        assert genre.name == 'Rock'
        assert genre.slug == 'rock'
        assert str(genre) == 'Rock'

    def test_genre_unique_name(self):
        """Test that genre names are unique."""
        GenreFactory(name='Rock', slug='rock')
        with pytest.raises(IntegrityError):
            GenreFactory(name='Rock', slug='rock-2')

    def test_genre_slug_generation(self):
        """Test automatic slug generation."""
        genre = GenreFactory(name='Heavy Metal')
        assert genre.slug == 'heavy-metal'


# =============================================================================
# Artist Model Tests
# =============================================================================

@pytest.mark.django_db
class TestArtistModel:
    """Tests for the Artist model."""

    def test_create_artist(self):
        """Test creating an artist."""
        artist = ArtistFactory(name='Test Artist')
        assert artist.name == 'Test Artist'
        assert str(artist) == 'Test Artist'

    def test_artist_unique_name(self):
        """Test that artist names are unique."""
        ArtistFactory(name='Unique Artist')
        with pytest.raises(IntegrityError):
            ArtistFactory(name='Unique Artist')

    def test_artist_genres_relationship(self):
        """Test artist-genre many-to-many relationship."""
        artist = ArtistFactory()
        genres = [GenreFactory() for _ in range(3)]
        artist.genres.add(*genres)
        assert artist.genres.count() == 3

    def test_artist_total_tracks_property(self):
        """Test the total_tracks property."""
        artist = ArtistFactory()
        album = AlbumFactory(artist=artist)
        for _ in range(5):
            TrackFactory(artist=artist, album=album)
        assert artist.total_tracks == 5

    def test_artist_total_albums_property(self):
        """Test the total_albums property."""
        artist = ArtistFactory()
        for _ in range(3):
            AlbumFactory(artist=artist)
        assert artist.total_albums == 3


# =============================================================================
# Album Model Tests
# =============================================================================

@pytest.mark.django_db
class TestAlbumModel:
    """Tests for the Album model."""

    def test_create_album(self):
        """Test creating an album."""
        artist = ArtistFactory()
        album = AlbumFactory(title='Test Album', artist=artist)
        assert album.title == 'Test Album'
        assert album.artist == artist
        assert 'Test Album' in str(album)

    def test_album_types(self):
        """Test different album types."""
        for album_type in ['album', 'single', 'ep', 'compilation']:
            album = AlbumFactory(album_type=album_type)
            assert album.album_type == album_type

    def test_album_unique_title_per_artist(self):
        """Test that album titles are unique per artist."""
        artist = ArtistFactory()
        AlbumFactory(title='Same Title', artist=artist)
        with pytest.raises(IntegrityError):
            AlbumFactory(title='Same Title', artist=artist)

    def test_album_duration_property(self):
        """Test the album duration calculation."""
        album = AlbumFactory()
        TrackFactory(album=album, duration=timedelta(minutes=3, seconds=30))
        TrackFactory(album=album, duration=timedelta(minutes=4, seconds=15))
        total = album.duration
        assert total == timedelta(minutes=7, seconds=45)


# =============================================================================
# Track Model Tests
# =============================================================================

@pytest.mark.django_db
class TestTrackModel:
    """Tests for the Track model."""

    def test_create_track(self):
        """Test creating a track."""
        track = TrackFactory(title='Test Track')
        assert track.title == 'Test Track'
        assert track.is_available is True

    def test_track_relationships(self):
        """Test track relationships."""
        artist = ArtistFactory()
        album = AlbumFactory(artist=artist)
        genre = GenreFactory()
        track = TrackFactory(artist=artist, album=album, genre=genre)
        assert track.artist == artist
        assert track.album == album
        assert track.genre == genre

    def test_track_play_count_default(self):
        """Test that play_count defaults to 0."""
        track = TrackFactory()
        from django.core.files.base import ContentFile
        # Factory sets random play_count, but we test the model default
        new_track = Track.objects.create(
            title='New Track',
            artist=track.artist,
            album=track.album,
            genre=track.genre,
            duration=timedelta(minutes=3),
            release_date=date.today(),
            audio_file=ContentFile(b'\xff\xfb\x90\x00' + b'\x00' * 100, name='test.mp3')
        )
        assert new_track.play_count == 0

    def test_track_explicit_flag(self):
        """Test the explicit content flag."""
        track = TrackFactory(explicit=True)
        assert track.explicit is True

    def test_track_availability(self):
        """Test track availability flag."""
        track = TrackFactory(is_available=False)
        assert track.is_available is False


# =============================================================================
# Playlist Model Tests
# =============================================================================

@pytest.mark.django_db
class TestPlaylistModel:
    """Tests for the Playlist model."""

    def test_create_playlist(self):
        """Test creating a playlist."""
        user = UserFactory()
        playlist = PlaylistFactory(owner=user, title='My Playlist')
        assert playlist.title == 'My Playlist'
        assert playlist.owner == user

    def test_playlist_track_list(self):
        """Test adding tracks to playlist."""
        playlist = PlaylistFactory()
        tracks = [TrackFactory() for _ in range(5)]
        playlist.track_list.add(*tracks)
        assert playlist.track_list.count() == 5

    def test_playlist_track_count_property(self):
        """Test the track_count property."""
        playlist = PlaylistFactory()
        tracks = [TrackFactory() for _ in range(3)]
        playlist.track_list.add(*tracks)
        assert playlist.track_count == 3

    def test_playlist_visibility(self):
        """Test playlist public/private visibility."""
        public_playlist = PlaylistFactory(is_public=True)
        private_playlist = PlaylistFactory(is_public=False)
        assert public_playlist.is_public is True
        assert private_playlist.is_public is False

    def test_playlist_collaborators(self):
        """Test collaborative playlist feature."""
        owner = UserFactory()
        collaborator = UserFactory()
        playlist = PlaylistFactory(owner=owner)
        playlist.collaborators.add(collaborator)
        assert collaborator in playlist.collaborators.all()

    def test_playlist_total_duration(self):
        """Test total duration calculation."""
        playlist = PlaylistFactory()
        track1 = TrackFactory(duration=timedelta(minutes=3, seconds=30))
        track2 = TrackFactory(duration=timedelta(minutes=4, seconds=15))
        playlist.track_list.add(track1, track2)
        assert playlist.total_duration == timedelta(minutes=7, seconds=45)


# =============================================================================
# Streaming Model Tests
# =============================================================================

@pytest.mark.django_db
class TestPlayHistoryModel:
    """Tests for the PlayHistory model."""

    def test_create_play_history(self):
        """Test creating play history entry."""
        history = PlayHistoryFactory()
        assert history.user is not None
        assert history.track is not None

    def test_play_history_context_choices(self):
        """Test valid context choices."""
        valid_contexts = ['album', 'playlist', 'search', 'radio', 'library']
        for context in valid_contexts:
            history = PlayHistoryFactory(context=context)
            assert history.context == context

    def test_play_history_completion(self):
        """Test completed flag."""
        completed = PlayHistoryFactory(completed=True)
        not_completed = PlayHistoryFactory(completed=False)
        assert completed.completed is True
        assert not_completed.completed is False


@pytest.mark.django_db
class TestUserFavoriteModel:
    """Tests for the UserFavorite model."""

    def test_create_favorite(self):
        """Test creating a favorite."""
        favorite = UserFavoriteFactory()
        assert favorite.user is not None
        assert favorite.track is not None

    def test_unique_user_track_favorite(self):
        """Test that user can only favorite a track once."""
        user = UserFactory()
        track = TrackFactory()
        UserFavoriteFactory(user=user, track=track)
        with pytest.raises(IntegrityError):
            UserFavoriteFactory(user=user, track=track)


@pytest.mark.django_db
class TestUserQueueModel:
    """Tests for the UserQueue model."""

    def test_create_queue(self):
        """Test creating a user queue."""
        user = UserFactory()
        from streaming.models import UserQueue
        queue = UserQueue.objects.create(user=user)
        assert queue.user == user
        assert queue.shuffle is False
        assert queue.repeat_mode == 'off'

    def test_queue_repeat_modes(self):
        """Test different repeat modes."""
        user = UserFactory()
        from streaming.models import UserQueue
        for mode in ['off', 'one', 'all']:
            queue = UserQueue.objects.create(user=UserFactory())
            queue.repeat_mode = mode
            queue.save()
            assert queue.repeat_mode == mode
