"""
Test factories for creating test data using factory_boy.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from datetime import timedelta, date
import random


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop('password', 'testpass123')
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class GenreFactory(DjangoModelFactory):
    """Factory for creating Genre instances."""

    class Meta:
        model = 'music.Genre'
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Genre {n}')
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-'))
    description = factory.Faker('sentence')


class ArtistFactory(DjangoModelFactory):
    """Factory for creating Artist instances."""

    class Meta:
        model = 'artist.Artist'
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Artist {n}')
    biography = factory.Faker('paragraph')
    is_verified = factory.Faker('boolean', chance_of_getting_true=30)

    @factory.post_generation
    def genres(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for genre in extracted:
                self.genres.add(genre)


class AlbumFactory(DjangoModelFactory):
    """Factory for creating Album instances."""

    class Meta:
        model = 'album.Album'

    title = factory.Sequence(lambda n: f'Album {n}')
    artist = factory.SubFactory(ArtistFactory)
    release_date = factory.Faker('date_between', start_date='-10y', end_date='today')
    album_type = factory.Iterator(['album', 'single', 'ep', 'compilation'])
    record_label = factory.Faker('company')


class TrackFactory(DjangoModelFactory):
    """Factory for creating Track instances."""

    class Meta:
        model = 'music.Track'

    title = factory.Sequence(lambda n: f'Track {n}')
    artist = factory.SubFactory(ArtistFactory)
    album = factory.SubFactory(AlbumFactory)
    genre = factory.SubFactory(GenreFactory)
    duration = factory.LazyFunction(lambda: timedelta(minutes=random.randint(2, 6), seconds=random.randint(0, 59)))
    release_date = factory.Faker('date_between', start_date='-5y', end_date='today')
    play_count = factory.Faker('random_int', min=0, max=1000000)
    is_available = True
    explicit = factory.Faker('boolean', chance_of_getting_true=20)
    audio_file = factory.LazyAttribute(
        lambda _: ContentFile(b'\xff\xfb\x90\x00' + b'\x00' * 100, name='test.mp3')
    )


class PlaylistFactory(DjangoModelFactory):
    """Factory for creating Playlist instances."""

    class Meta:
        model = 'playlist.Playlist'

    title = factory.Sequence(lambda n: f'Playlist {n}')
    description = factory.Faker('sentence')
    owner = factory.SubFactory(UserFactory)
    is_public = factory.Faker('boolean', chance_of_getting_true=50)

    @factory.post_generation
    def tracks(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for track in extracted:
                self.track_list.add(track)


class PlayHistoryFactory(DjangoModelFactory):
    """Factory for creating PlayHistory instances."""

    class Meta:
        model = 'streaming.PlayHistory'

    user = factory.SubFactory(UserFactory)
    track = factory.SubFactory(TrackFactory)
    completed = factory.Faker('boolean', chance_of_getting_true=80)
    duration_listened = factory.LazyFunction(lambda: timedelta(minutes=random.randint(1, 5)))
    context = factory.Iterator(['album', 'playlist', 'search', 'radio', 'library'])


class UserFavoriteFactory(DjangoModelFactory):
    """Factory for creating UserFavorite instances."""

    class Meta:
        model = 'streaming.UserFavorite'

    user = factory.SubFactory(UserFactory)
    track = factory.SubFactory(TrackFactory)
