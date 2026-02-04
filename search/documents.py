"""
Elasticsearch document definitions using django-elasticsearch-dsl.

Each document maps a Django model to an Elasticsearch index,
defining which fields are indexed and how they are analysed.
"""

from django_elasticsearch_dsl import Document, fields, Index
from django_elasticsearch_dsl.registries import registry

from music.models import Track, Genre
from artist.models import Artist
from album.models import Album

# ---------------------------------------------------------------------------
# Index definitions
# ---------------------------------------------------------------------------

TRACK_INDEX = Index('tracks')
TRACK_INDEX.settings(
    number_of_shards=1,
    number_of_replicas=0,
    analysis={
        'analyzer': {
            'autocomplete': {
                'type': 'custom',
                'tokenizer': 'standard',
                'filter': ['lowercase', 'autocomplete_filter'],
            },
        },
        'filter': {
            'autocomplete_filter': {
                'type': 'edge_ngram',
                'min_gram': 2,
                'max_gram': 20,
            },
        },
    },
)

ARTIST_INDEX = Index('artists')
ARTIST_INDEX.settings(number_of_shards=1, number_of_replicas=0)

ALBUM_INDEX = Index('albums')
ALBUM_INDEX.settings(number_of_shards=1, number_of_replicas=0)


# ---------------------------------------------------------------------------
# Track document
# ---------------------------------------------------------------------------

@registry.register_document
@TRACK_INDEX.doc_type
class TrackDocument(Document):
    """Elasticsearch document for Track model."""

    # Nested / related fields
    artist = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField(
            analyzer='autocomplete',
            fields={'raw': fields.KeywordField()},
        ),
    })
    album = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'title': fields.TextField(
            analyzer='autocomplete',
            fields={'raw': fields.KeywordField()},
        ),
    })
    genre = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField(fields={'raw': fields.KeywordField()}),
        'slug': fields.KeywordField(),
    })

    # Track fields
    title = fields.TextField(
        analyzer='autocomplete',
        fields={'raw': fields.KeywordField()},
    )
    lyrics = fields.TextField()
    explicit = fields.BooleanField()
    play_count = fields.IntegerField()
    release_date = fields.DateField()
    duration_seconds = fields.FloatField()
    is_available = fields.BooleanField()
    created_at = fields.DateField()

    class Django:
        model = Track
        related_models = [Artist, Album, Genre]

    def get_instances_from_related(self, related_instance):
        """Return Track instances when a related model changes."""
        if isinstance(related_instance, Artist):
            return related_instance.tracks.all()
        if isinstance(related_instance, Album):
            return related_instance.tracks.all()
        if isinstance(related_instance, Genre):
            return related_instance.tracks.all()
        return []

    def prepare_duration_seconds(self, instance):
        return instance.duration_seconds


# ---------------------------------------------------------------------------
# Artist document
# ---------------------------------------------------------------------------

@registry.register_document
@ARTIST_INDEX.doc_type
class ArtistDocument(Document):
    name = fields.TextField(
        analyzer='autocomplete',
        fields={'raw': fields.KeywordField()},
    )
    biography = fields.TextField()
    is_verified = fields.BooleanField()
    genres = fields.NestedField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField(fields={'raw': fields.KeywordField()}),
    })

    class Django:
        model = Artist

    def prepare_genres(self, instance):
        return [{'id': g.id, 'name': g.name} for g in instance.genres.all()]


# ---------------------------------------------------------------------------
# Album document
# ---------------------------------------------------------------------------

@registry.register_document
@ALBUM_INDEX.doc_type
class AlbumDocument(Document):
    title = fields.TextField(
        analyzer='autocomplete',
        fields={'raw': fields.KeywordField()},
    )
    artist = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField(fields={'raw': fields.KeywordField()}),
    })
    album_type = fields.KeywordField()
    release_date = fields.DateField()

    class Django:
        model = Album
        related_models = [Artist]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Artist):
            return Album.objects.filter(artist=related_instance)
        return []
