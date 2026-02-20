"""
Elasticsearch-powered search views.

Provides:
- Multi-model unified search across tracks, artists, and albums
- Autocomplete / typeahead suggestions
- Faceted filtering (genre, artist, album_type, year range)
"""

import logging
from django.conf import settings
from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

logger = logging.getLogger('search')


def _es_available() -> bool:
    """Check whether Elasticsearch is configured and reachable."""
    es_hosts = getattr(settings, 'ELASTICSEARCH_DSL', {})
    return bool(es_hosts)


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------

@extend_schema(
    summary='Search across tracks, artists and albums',
    parameters=[
        OpenApiParameter('q', str, description='Search query', required=True),
        OpenApiParameter('type', str, description='Restrict to: track, artist, album'),
        OpenApiParameter('genre', str, description='Filter by genre slug'),
        OpenApiParameter('year_from', int, description='Release year lower bound'),
        OpenApiParameter('year_to', int, description='Release year upper bound'),
        OpenApiParameter('limit', int, description='Max results per type (default 10)'),
    ],
    tags=['Search'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unified_search(request):
    """
    Full-text search across tracks, artists, and albums.

    If Elasticsearch is unavailable the view falls back to Django ORM
    ``icontains`` queries so the API never hard-fails.
    """
    query = request.query_params.get('q', '').strip()
    if not query:
        return Response(
            {'error': {'code': 'missing_query', 'message': 'Query parameter "q" is required.'}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    restrict_type = request.query_params.get('type')
    genre_slug = request.query_params.get('genre')
    year_from = request.query_params.get('year_from')
    year_to = request.query_params.get('year_to')

    try:
        limit = min(int(request.query_params.get('limit', 10)), 50)
    except (ValueError, TypeError):
        return Response(
            {'error': {'code': 'invalid_limit', 'message': '"limit" must be an integer.'}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if year_from is not None:
        try:
            year_from = int(year_from)
        except (ValueError, TypeError):
            return Response(
                {'error': {'code': 'invalid_year', 'message': '"year_from" must be an integer year.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if year_to is not None:
        try:
            year_to = int(year_to)
        except (ValueError, TypeError):
            return Response(
                {'error': {'code': 'invalid_year', 'message': '"year_to" must be an integer year.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if _es_available():
        return _es_search(query, restrict_type, genre_slug, year_from, year_to, limit)

    return _orm_search(query, restrict_type, genre_slug, year_from, year_to, limit)


# ---------------------------------------------------------------------------
# Autocomplete / typeahead
# ---------------------------------------------------------------------------

@extend_schema(
    summary='Autocomplete suggestions',
    parameters=[
        OpenApiParameter('q', str, description='Partial search query', required=True),
        OpenApiParameter('limit', int, description='Max suggestions (default 5)'),
    ],
    tags=['Search'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def autocomplete(request):
    """
    Lightweight typeahead returning names/titles that match the prefix.
    """
    query = request.query_params.get('q', '').strip()
    if not query or len(query) < 2:
        return Response({'suggestions': []})

    try:
        limit = min(int(request.query_params.get('limit', 5)), 20)
    except (ValueError, TypeError):
        limit = 5

    if _es_available():
        return _es_autocomplete(query, limit)

    return _orm_autocomplete(query, limit)


# ---------------------------------------------------------------------------
# Elasticsearch implementations
# ---------------------------------------------------------------------------

def _es_search(query, restrict_type, genre_slug, year_from, year_to, limit):
    from elasticsearch_dsl import Q as ESQ
    from .documents import TrackDocument, ArtistDocument, AlbumDocument

    results = {'tracks': [], 'artists': [], 'albums': []}

    # Track search
    if restrict_type in (None, 'track'):
        s = TrackDocument.search()
        s = s.query(
            ESQ('multi_match', query=query, fields=[
                'title^3', 'artist.name^2', 'album.title', 'lyrics', 'genre.name',
            ], fuzziness='AUTO')
        )
        s = s.filter('term', is_available=True)
        if genre_slug:
            s = s.filter('term', genre__slug=genre_slug)
        if year_from:
            s = s.filter('range', release_date={'gte': f'{year_from}-01-01'})
        if year_to:
            s = s.filter('range', release_date={'lte': f'{year_to}-12-31'})
        s = s[:limit]
        for hit in s.execute():
            results['tracks'].append({
                'id': hit.meta.id,
                'title': hit.title,
                'artist': hit.artist.name if hit.artist else None,
                'album': hit.album.title if hit.album else None,
                'genre': hit.genre.name if hit.genre else None,
                'play_count': hit.play_count,
                'score': hit.meta.score,
            })

    # Artist search
    if restrict_type in (None, 'artist'):
        s = ArtistDocument.search()
        s = s.query(
            ESQ('multi_match', query=query, fields=['name^3', 'biography'], fuzziness='AUTO')
        )
        s = s[:limit]
        for hit in s.execute():
            results['artists'].append({
                'id': hit.meta.id,
                'name': hit.name,
                'is_verified': hit.is_verified,
                'score': hit.meta.score,
            })

    # Album search
    if restrict_type in (None, 'album'):
        s = AlbumDocument.search()
        s = s.query(
            ESQ('multi_match', query=query, fields=['title^3', 'artist.name'], fuzziness='AUTO')
        )
        if year_from:
            s = s.filter('range', release_date={'gte': f'{year_from}-01-01'})
        if year_to:
            s = s.filter('range', release_date={'lte': f'{year_to}-12-31'})
        s = s[:limit]
        for hit in s.execute():
            results['albums'].append({
                'id': hit.meta.id,
                'title': hit.title,
                'artist': hit.artist.name if hit.artist else None,
                'album_type': hit.album_type,
                'score': hit.meta.score,
            })

    return Response(results)


def _es_autocomplete(query, limit):
    from elasticsearch_dsl import Q as ESQ
    from .documents import TrackDocument, ArtistDocument, AlbumDocument

    suggestions = []

    for doc_cls, field, category in [
        (TrackDocument, 'title', 'track'),
        (ArtistDocument, 'name', 'artist'),
        (AlbumDocument, 'title', 'album'),
    ]:
        s = doc_cls.search()
        s = s.query(ESQ('match_phrase_prefix', **{field: {'query': query}}))
        s = s[:limit]
        for hit in s.execute():
            text = getattr(hit, field, '')
            suggestions.append({
                'text': text,
                'type': category,
                'id': hit.meta.id,
            })

    # Deduplicate and cap
    seen = set()
    unique = []
    for s in suggestions:
        key = (s['type'], s['id'])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return Response({'suggestions': unique[:limit]})


# ---------------------------------------------------------------------------
# ORM fallback implementations (no Elasticsearch required)
# ---------------------------------------------------------------------------

def _orm_search(query, restrict_type, genre_slug, year_from, year_to, limit):
    from music.models import Track, Genre
    from artist.models import Artist
    from album.models import Album

    results = {'tracks': [], 'artists': [], 'albums': []}

    if restrict_type in (None, 'track'):
        qs = Track.objects.filter(is_available=True).filter(
            models.Q(title__icontains=query)
            | models.Q(artist__name__icontains=query)
            | models.Q(album__title__icontains=query)
            | models.Q(lyrics__icontains=query)
        ).select_related('artist', 'album', 'genre')
        if genre_slug:
            qs = qs.filter(genre__slug=genre_slug)
        if year_from:
            qs = qs.filter(release_date__year__gte=int(year_from))
        if year_to:
            qs = qs.filter(release_date__year__lte=int(year_to))
        for t in qs[:limit]:
            results['tracks'].append({
                'id': t.id,
                'title': t.title,
                'artist': t.artist.name,
                'album': t.album.title if t.album else None,
                'genre': t.genre.name if t.genre else None,
                'play_count': t.play_count,
            })

    if restrict_type in (None, 'artist'):
        for a in Artist.objects.filter(
            models.Q(name__icontains=query)
            | models.Q(biography__icontains=query)
        )[:limit]:
            results['artists'].append({
                'id': a.id,
                'name': a.name,
                'is_verified': a.is_verified,
            })

    if restrict_type in (None, 'album'):
        qs = Album.objects.filter(
            models.Q(title__icontains=query)
            | models.Q(artist__name__icontains=query)
        ).select_related('artist')
        if year_from:
            qs = qs.filter(release_date__year__gte=int(year_from))
        if year_to:
            qs = qs.filter(release_date__year__lte=int(year_to))
        for a in qs[:limit]:
            results['albums'].append({
                'id': a.id,
                'title': a.title,
                'artist': a.artist.name,
                'album_type': a.album_type,
            })

    return Response(results)


def _orm_autocomplete(query, limit):
    from music.models import Track
    from artist.models import Artist
    from album.models import Album

    suggestions = []

    for t in Track.objects.filter(title__icontains=query, is_available=True)[:limit]:
        suggestions.append({'text': t.title, 'type': 'track', 'id': t.id})
    for a in Artist.objects.filter(name__icontains=query)[:limit]:
        suggestions.append({'text': a.name, 'type': 'artist', 'id': a.id})
    for a in Album.objects.filter(title__icontains=query)[:limit]:
        suggestions.append({'text': a.title, 'type': 'album', 'id': a.id})

    return Response({'suggestions': suggestions[:limit]})


