# Spotifylookalike – Production Music Streaming Backend

A production-ready REST API backend for a music streaming service, built with Django REST Framework. Supports audio streaming with HTTP Range requests, background transcoding via FFmpeg and Celery, full-text search with Elasticsearch, real-time WebSocket notifications, and JWT authentication.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Application Flow of Control](#application-flow-of-control)
   - [HTTP Request Lifecycle](#http-request-lifecycle)
   - [Audio Streaming Flow](#audio-streaming-flow)
   - [Transcoding Pipeline](#transcoding-pipeline)
   - [Search Flow](#search-flow)
   - [WebSocket Flow](#websocket-flow)
4. [Module Reference](#module-reference)
   - [Project Package (`spotify/`)](#project-package-spotify)
   - [Core App](#core-app)
   - [Music App](#music-app)
   - [Artist App](#artist-app)
   - [Album App](#album-app)
   - [Playlist App](#playlist-app)
   - [Authentication App](#authentication-app)
   - [Streaming App](#streaming-app)
   - [Transcoding App](#transcoding-app)
   - [Search App](#search-app)
   - [Realtime App](#realtime-app)
5. [API Endpoints](#api-endpoints)
6. [Running Locally](#running-locally)
7. [Docker Deployment](#docker-deployment)
8. [Running Tests](#running-tests)

---

## Architecture Overview

```
                     ┌─────────────────────────────────────────────────┐
                     │                 NGINX (Port 80/443)              │
                     │         Reverse proxy + static files             │
                     └──────┬────────────────────────┬─────────────────┘
                            │ /api/ /health/ /admin/  │ /ws/
                            ▼                         ▼
              ┌─────────────────────┐    ┌─────────────────────────┐
              │  Gunicorn / WSGI    │    │    Daphne / ASGI         │
              │  HTTP API (8000)    │    │  WebSocket Server (8001) │
              └────────┬────────────┘    └──────────┬──────────────┘
                       │                            │
                       ▼                            ▼
              ┌─────────────────────────────────────────────────────┐
              │               Django Application                    │
              │  ┌─────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐  │
              │  │  Music  │ │ Artist │ │ Playlist │ │Streaming│  │
              │  └─────────┘ └────────┘ └──────────┘ └─────────┘  │
              │  ┌──────────────┐ ┌────────┐ ┌──────────────────┐  │
              │  │Transcoding   │ │ Search │ │    Realtime (WS)  │  │
              │  └──────────────┘ └────────┘ └──────────────────┘  │
              └───────────────┬─────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────────────────┐
              ▼               ▼                           ▼
      ┌──────────────┐ ┌──────────┐              ┌──────────────────┐
      │  PostgreSQL  │ │  Redis   │              │  Elasticsearch   │
      │   Database   │ │Cache/MQ  │              │  Search Index    │
      └──────────────┘ └────┬─────┘              └──────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Celery Worker │
                    │ (Transcoding) │
                    └───────────────┘
```

The application is split into **eight Django apps**, each with a single clear responsibility:

| App | Responsibility |
|-----|----------------|
| `core` | Shared permissions, pagination, exceptions, middleware, logging |
| `music` | Tracks and genres – the central content resource |
| `artist` | Artist profiles and discography aggregation |
| `album` | Album management and track grouping |
| `playlist` | User-created playlists with collaborative editing |
| `authentication` | JWT token issuance and legacy token auth |
| `streaming` | Audio delivery, play history, favourites, queue |
| `transcoding` | FFmpeg-based format conversion (async via Celery) |
| `search` | Full-text search (Elasticsearch) with ORM fallback |
| `realtime` | WebSocket push notifications (Django Channels) |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web framework | Django 4.x + DRF | HTTP routing, ORM, validation |
| Auth | SimpleJWT | Stateless JWT access/refresh tokens |
| Async HTTP | Gunicorn | Multi-worker WSGI server |
| WebSocket | Django Channels + Daphne | Real-time push notifications |
| Task queue | Celery + Redis | Background audio transcoding |
| Cache | Redis | Response caching, Channel layer |
| Search | Elasticsearch + django-elasticsearch-dsl | Full-text search |
| Audio processing | FFmpeg | Audio transcoding, waveform generation |
| Database | PostgreSQL (SQLite for dev) | Persistent storage |
| API docs | drf-spectacular | Auto-generated OpenAPI/Swagger |
| Proxy | Nginx | SSL termination, static files, WS proxy |
| Containers | Docker Compose | 8-service orchestration |

---

## Application Flow of Control

### HTTP Request Lifecycle

Every HTTP request follows this path through the stack:

```
Client Request
      │
      ▼
┌─────────────────────────────────────────────────────┐
│ 1. Nginx                                            │
│    - Terminates SSL                                 │
│    - Routes /ws/ to Daphne, rest to Gunicorn        │
│    - Rate-limits via limit_req zones                │
│    - Serves /static/ and /media/ directly           │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 2. Django Middleware Stack (settings.MIDDLEWARE)    │
│    a. SecurityMiddleware         – HTTPS redirects  │
│    b. RequestLoggingMiddleware   – request ID, timer│
│    c. CacheControlMiddleware     – Cache headers    │
│    d. SessionMiddleware          – session cookies  │
│    e. CorsMiddleware             – CORS headers     │
│    f. AuthenticationMiddleware   – session user     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 3. URL Router (spotify/urls.py)                     │
│    /api/v1/tracks/     → TrackViewSet               │
│    /api/v1/stream/{id}/ → stream_track()           │
│    /api/v1/search/     → unified_search()           │
│    /api/v1/transcode/  → trigger_transcode()        │
│    /api/v1/auth/token/ → SimpleJWT TokenObtainView  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 4. DRF Permission Checks                            │
│    - JWTAuthentication validates Bearer token       │
│    - Permission class runs (IsAdminOrReadOnly, etc) │
│    - Throttle class checks rate limit               │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 5. ViewSet / View                                   │
│    - get_queryset() builds and filters queryset     │
│    - get_serializer_class() picks the right one     │
│    - Business logic executes                        │
│    - Serializer.to_representation() shapes response │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 6. Serializer                                       │
│    - Validates input on write operations            │
│    - Serializes queryset/instance to dict           │
│    - Computed fields (SerializerMethodField)        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              JSON Response to Client
```

---

### Audio Streaming Flow

This is the core feature: RFC 7233 HTTP Range request support for seeking.

```
Client: GET /api/v1/stream/42/
        Headers: Range: bytes=500000-999999
                 Authorization: Bearer <token>
        │
        ▼
stream_track(request, track_id=42)
        │
        ├─ 1. Authenticate user (JWT check)
        │
        ├─ 2. Look up Track.objects.get(pk=42)
        │      └─ 404 if not found or not available
        │
        ├─ 3. get_content_type(file_path)
        │      └─ Determine MIME type (audio/mpeg, audio/ogg, etc.)
        │
        ├─ 4. Parse Range header
        │      parse_range_header("bytes=500000-999999", file_size)
        │      └─ Returns (500000, 999999)
        │      └─ Returns (None, None) if no Range header
        │
        ├─ 5a. RANGE REQUEST → 206 Partial Content
        │       - If start ≥ file_size → 416 Range Not Satisfiable
        │       - Clamp end to file_size - 1
        │       - Headers: Content-Range, Content-Length, Accept-Ranges
        │       - StreamingHttpResponse via file_iterator(start, end)
        │
        ├─ 5b. FULL REQUEST → 200 OK
        │       - Headers: Content-Length, Accept-Ranges
        │       - StreamingHttpResponse via file_iterator()
        │
        ├─ 6. Record play history (non-blocking)
        │      PlayHistory.objects.create(user, track, context)
        │
        └─ 7. Increment play count (atomic)
               Track.objects.filter(pk=42).update(
                   play_count=F('play_count') + 1
               )
```

---

### Transcoding Pipeline

Audio transcoding is asynchronous — the API returns immediately and the conversion runs in the background.

```
Admin: POST /api/v1/transcode/42/transcode/all/
        │
        ▼
trigger_transcode_all(request, track_id=42)
        │
        ├─ 1. Verify user is admin (IsAdminOrReadOnly)
        ├─ 2. Look up Track
        └─ 3. Dispatch Celery task: transcode_all_qualities.delay(42)
                │
                ▼ (runs asynchronously on Celery worker)
        transcode_all_qualities(track_id=42)
                │
                ├─ Dispatch 4 child tasks (one per quality preset):
                │   transcode_track.delay(42, quality='low')
                │   transcode_track.delay(42, quality='medium')
                │   transcode_track.delay(42, quality='high')
                │   transcode_track.delay(42, quality='lossless')
                │
                └─ Each transcode_track(track_id, quality):
                        │
                        ├─ 1. Idempotency check:
                        │      Already have completed TranscodedTrack? → skip
                        │
                        ├─ 2. Create/update TranscodedTrack status='processing'
                        │
                        ├─ 3. service.transcode(
                        │         input_path,
                        │         output_path,
                        │         codec=preset['codec'],
                        │         bitrate=preset['bitrate']
                        │      )
                        │      └─ Calls FFmpeg subprocess
                        │
                        ├─ 4. On success:
                        │      - Save transcoded_file path
                        │      - Record file_size
                        │      - Set status='completed'
                        │
                        └─ 5. On failure:
                               - Set status='failed', error_message
                               - Retry up to 3 times (60s backoff)
```

---

### Search Flow

Search uses Elasticsearch when available, with a transparent ORM fallback.

```
Client: GET /api/v1/search/?q=beatles&type=track&genre=rock&year_from=1965
        │
        ▼
unified_search(request)
        │
        ├─ 1. Validate parameters:
        │      - Empty/blank q → 400
        │      - Non-integer limit, year_from, year_to → 400
        │      - Cap limit at 50
        │
        ├─ 2. _es_available()?
        │
        ├─ YES → _es_search(query, type, genre, year_from, year_to, limit)
        │          │
        │          ├─ TrackDocument.search() with multi_match + fuzziness
        │          ├─ ArtistDocument.search() if type not restricted
        │          └─ AlbumDocument.search() if type not restricted
        │
        └─ NO  → _orm_search(query, type, genre, year_from, year_to, limit)
                   │
                   ├─ Track.objects.filter(Q(title__icontains=q)|...)
                   ├─ Artist.objects.filter(Q(name__icontains=q)|...)
                   └─ Album.objects.filter(Q(title__icontains=q)|...)
        │
        ▼
Response: { "tracks": [...], "artists": [...], "albums": [...] }
```

---

### WebSocket Flow

```
Client (browser/app)
        │
        │  ws://host/ws/notifications/?token=<jwt>
        ▼
Nginx → Daphne (ASGI)
        │
        ▼
JWTAuthMiddleware.__call__(scope, receive, send)
        │
        ├─ Extract token from query string
        ├─ get_user_from_token(token_str)
        │    └─ AccessToken(token_str) → User.objects.get(pk=payload['user_id'])
        │
        ├─ Valid token → scope['user'] = user → pass to consumer
        └─ Invalid token → close with code 4001
        │
        ▼
NotificationConsumer.connect()
        │
        ├─ self.accept()
        └─ channel_layer.group_add(f"user_{user_id}", self.channel_name)

─────────────── Server-side event (e.g. new track uploaded) ───────────────
        │
        ▼
realtime/signals.py: notify_new_track (post_save signal on Track)
        │
        └─ channel_layer.group_send(
               f"user_{user_id}",
               {"type": "track_released", "track": {...}}
           )
        │
        ▼
NotificationConsumer.track_released(event)
        │
        └─ self.send_json(event)  → client receives JSON message

─────────────── Client disconnect ─────────────────────────────────────────
NotificationConsumer.disconnect(close_code)
        │
        └─ channel_layer.group_discard(group_name, self.channel_name)
```

---

## Module Reference

### Project Package (`spotify/`)

#### `spotify/settings.py`

The single source of truth for all configuration. Every setting is driven by an environment variable with a safe default.

| Function / Setting | Purpose |
|--------------------|---------|
| `get_env(key, default, cast)` | Type-casting environment variable reader. Avoids scattered `os.environ.get()` calls and ensures booleans/integers are cast correctly. |
| `INSTALLED_APPS` | Registers all ten apps plus third-party packages (DRF, Channels, drf-spectacular). |
| `DATABASES` | Switches between SQLite (local dev) and PostgreSQL based on `DATABASE_ENGINE` env var. |
| `CACHES` | Redis-backed cache in production; falls back to local memory cache. |
| `CHANNEL_LAYERS` | Redis-backed Channels layer for WebSocket group messaging. |
| `REST_FRAMEWORK` | Configures JWT as default authentication, rate throttling, pagination, and the custom exception handler. |
| `SIMPLE_JWT` | Token lifetimes, rotation policy, and blacklist settings for JWT authentication. |
| `ELASTICSEARCH_DSL` | Points Django-Elasticsearch-DSL at the cluster; empty dict disables ES and enables ORM fallback. |
| `CELERY_*` | Broker URL, result backend, task serialiser, and timezone for the async worker. |

#### `spotify/urls.py`

The root URL router. All modern endpoints live under `/api/v1/` and are registered via a DRF `DefaultRouter`. Legacy endpoints remain mounted directly for backward compatibility.

```
/api/v1/tracks/          → TrackViewSet
/api/v1/genres/          → GenreViewSet
/api/v1/artists/         → ArtistViewSet
/api/v1/albums/          → AlbumViewSet
/api/v1/playlists/       → PlaylistViewSet
/api/v1/stream/          → streaming.urls
/api/v1/transcode/       → transcoding.urls
/api/v1/search/          → search.urls
/api/v1/auth/token/      → SimpleJWT TokenObtainPairView
/api/docs/               → Swagger UI
/health/                 → health_check view
```

#### `spotify/asgi.py`

Configures the `ProtocolTypeRouter` that lets a single Daphne process handle both normal HTTP (forwarded to Django's WSGI-compatible handler) and WebSocket connections (forwarded to `URLRouter` with JWT middleware applied).

#### `spotify/wsgi.py`

Standard Django WSGI entrypoint used by Gunicorn for the HTTP API server. WebSocket traffic is handled separately by Daphne.

---

### Core App

Shared infrastructure used by every other app. Contains no models.

#### `core/permissions.py`

All custom permission classes inherit from DRF's `BasePermission` and implement `has_object_permission`.

| Class | Logic | Used by |
|-------|-------|---------|
| `IsOwner` | SAFE methods allowed to any authenticated user; writes require `obj.owner == request.user` or `obj.user == request.user` | Play history, queue |
| `IsOwnerOrReadOnly` | Identical logic to `IsOwner` — kept as a named alias for semantic clarity in ViewSet declarations | Playlists |
| `IsAdminOrReadOnly` | SAFE methods for anyone; write methods restricted to `request.user.is_staff` | Tracks, albums, genres |
| `IsArtistOwner` | Admin staff OR `obj.user == request.user` can write; reads are open | Artist management |
| `CanManagePlaylist` | Owner: full access. Collaborators: only `add_tracks`/`remove_tracks` actions. Others: read-only if `is_public=True` | Playlist ViewSet |

#### `core/pagination.py`

Three pagination strategies to match different response sizes:

| Class | page_size | max_page_size | Use case |
|-------|-----------|---------------|----------|
| `StandardResultsSetPagination` | 20 | 100 | Default list endpoints |
| `LargeResultsSetPagination` | 50 | 200 | Search results |
| `TrackCursorPagination` | 20 | — | Infinite-scroll track lists (keyset pagination, no page-count leakage) |

#### `core/middleware.py`

**`RequestLoggingMiddleware`**
- `process_request(request)` — Records `_start_time` on the request and generates a UUID `X-Request-ID` header. This ID propagates through logs so a single request can be traced across multiple log lines.
- `process_response(request, response)` — Calculates elapsed milliseconds, logs method, path, status code, duration, user, and IP. Adds `X-Request-ID` and `X-Response-Time` headers to the outbound response.
- `get_client_ip(request)` — Reads the real client IP from `X-Forwarded-For` (set by Nginx) with a fallback to `REMOTE_ADDR`. Important for accurate rate limiting and audit logs behind a proxy.

**`CacheControlMiddleware`**
- `process_response(request, response)` — Sets `Cache-Control` headers based on URL pattern. Auth and admin paths get `no-store`. Static assets get `max-age=31536000, immutable`. API responses get `max-age=300, s-maxage=60`. This prevents browsers from caching sensitive data while allowing CDN caching of public API responses.

#### `core/exceptions.py`

Custom exception hierarchy with HTTP status codes baked in. The `custom_exception_handler` is registered in `settings.REST_FRAMEWORK['EXCEPTION_HANDLER']` and converts every exception — including Django's `Http404`, `PermissionDenied`, and database `IntegrityError` — into a consistent JSON envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "Track matching query does not exist.",
    "status": 404
  }
}
```

This means API consumers never receive an unexpected HTML error page.

| Exception class | HTTP status |
|-----------------|-------------|
| `NotFoundError` | 404 |
| `ValidationError` | 400 |
| `AuthenticationError` | 401 |
| `PermissionDeniedError` | 403 |
| `ConflictError` | 409 |
| `RateLimitError` | 429 |
| `StreamingError` | 500 |

#### `core/logging.py`

**`JSONFormatter.format(record)`** — Converts every log record to a single-line JSON object. Structured logs are parseable by log aggregators (Datadog, ELK, CloudWatch) without regex fragility.

**`get_logger(name)`** — Returns a logger namespaced under `spotify.<name>`. All app-level logging should use this instead of `logging.getLogger(__name__)` to inherit the JSON formatter configuration.

---

### Music App

The central content resource. Every other app (streaming, search, transcoding) references `Track`.

#### `music/models.py`

**`Genre`**
- `save()` — Overrides Django's default save to auto-generate a URL-safe `slug` from `name` using `slugify()` if `slug` is empty. Slugs are used in search filters and clean URLs (`/genres/hip-hop/`).
- `__str__()` — Returns the genre name for admin list display.

**`Track`**
The core data model. Key fields: `audio_file` (FileField/S3), `duration` (DurationField), `play_count` (int), `is_available` (bool), `lyrics`, `waveform_data` (JSON), `bitrate`.

- `duration_seconds` (property) — Converts `timedelta` to total seconds. Used by the streaming layer to calculate seek positions.
- `formatted_duration` (property) — Converts duration to human-readable `MM:SS` or `HH:MM:SS`. Used by serializers without requiring a template tag.

#### `music/serializers.py`

Three serializers per the Three-Tier Pattern:

**`TrackListSerializer`** — Minimal fields (`id`, `title`, `artist_name`, `album_title`, `duration`, `play_count`, `is_available`, `cover_art`). Used for list endpoints where returning full nested objects would cause N+1 queries. `artist_name` and `album_title` are denormalized string fields to avoid extra joins.

**`TrackDetailSerializer`** — Full fields plus computed ones:
- `get_stream_url(obj)` — Constructs the streaming endpoint URL (`/api/v1/stream/{id}/`). This is the URL clients use to actually play audio.
- Inherits `artist_name`, `album_title`, adds `lyrics`, `waveform_data`, `bitrate`, `formatted_duration`.

**`TrackCreateUpdateSerializer`**
- `validate_audio_file(value)` — Enforces a 100 MB file size cap. Raises a DRF `ValidationError` with a clear message before the file is stored, preventing disk-filling attacks.

**`GenreSerializer`**
- `get_track_count(obj)` — Returns `obj.track_count` if the queryset was annotated (avoids a database query), otherwise falls back to `obj.tracks.count()`. This dual-path approach lets the ViewSet optimise list responses with a single annotation while still returning the correct value for individual genre objects.

#### `music/views.py`

**`TrackViewSet`** — `ModelViewSet` with `IsAdminOrReadOnly` permission (anyone reads, only admins write).

| Method | Description |
|--------|-------------|
| `get_serializer_class()` | Returns `TrackListSerializer` for `list`, `TrackCreateUpdateSerializer` for `create`/`update`/`partial_update`, `TrackDetailSerializer` otherwise. Avoids over-fetching on list pages. |
| `list(request)` | Overrides default list to add a `cache_page(300)` decorator effect — the full track list is cached in Redis for 5 minutes, dramatically reducing DB load on popular endpoints. |
| `top(request)` | Returns the top N tracks ordered by `play_count`. N defaults to 10, configurable via `?limit=`. |
| `recent(request)` | Returns the 20 most recently created tracks, useful for "new arrivals" UI components. |
| `by_genre(request, genre_slug)` | Filters tracks by genre slug. Uses `TrackCursorPagination` for infinite scroll. |
| `play(request, pk)` | Atomically increments `play_count` using `F('play_count') + 1` — prevents race conditions when multiple users play the same track simultaneously. Returns the new count. |

**`GenreViewSet`**
- `get_queryset()` — Annotates genres with `track_count=Count('tracks')` so `TrackListSerializer.get_track_count()` avoids a per-genre query.
- `tracks(request, slug)` — Returns paginated tracks in a genre.

---

### Artist App

#### `artist/models.py`

**`Artist`** — Stores `name`, `biography`, `image`, `website`, `is_verified`, `genres` (M2M). Indexed on `name` for search performance.

- `total_tracks` (property) — `Track.objects.filter(artist=self).count()`. Used in list views to show artist stats without loading all tracks.
- `total_albums` (property) — `Album.objects.filter(artist=self).count()`. Same pattern.

#### `artist/serializers.py`

**`ArtistListSerializer`** — Lightweight, with computed fields:
- `get_genre_names(obj)` — Returns a flat list of genre name strings. Requires `prefetch_related('genres')` on the queryset to avoid N+1.
- `get_track_count(obj)` / `get_album_count(obj)` — Annotation-aware count getters.

**`ArtistDetailSerializer`**
- `get_total_plays(obj)` — Aggregates `Sum('tracks__play_count')` across all the artist's tracks. Shows the artist's total audience engagement.

#### `artist/views.py`

**`ArtistViewSet`**

| Method | Description |
|--------|-------------|
| `get_queryset()` | Prefetches genres and annotates `track_count`, `album_count` to prevent N+1 queries on list pages. |
| `get_serializer_class()` | `ArtistListSerializer` for list, `ArtistDetailSerializer` for detail. |
| `tracks(request, pk)` | Paginated available tracks by this artist, ordered by album then track number. |
| `albums(request, pk)` | Paginated albums by this artist ordered by release date desc. |
| `top(request)` | Returns top 20 artists by total track play count using a `Sum` aggregation — powers "Popular Artists" carousels. |

---

### Album App

#### `album/models.py`

**`Album`** — Stores `title`, `artist` (FK), `release_date`, `cover_art`, `album_type` (album/single/EP/compilation), `record_label`. Unique constraint on `(artist, title)` prevents duplicate albums.

- `duration` (property) — `Track.objects.filter(album=self).aggregate(Sum('duration'))['duration__sum']`. Returns total play time for display on album detail pages.

#### `album/serializers.py`

**`AlbumDetailSerializer`**
- `get_track_count(obj)` — Count of tracks in the album.
- `get_total_duration(obj)` — Formatted aggregate duration using the `Album.duration` property.
- `get_total_plays(obj)` — Sum of `play_count` across all tracks in the album. Shows album popularity without requiring the client to sum per-track counts.

#### `album/views.py`

**`AlbumViewSet`**

| Method | Description |
|--------|-------------|
| `get_queryset()` | `select_related('artist')` to avoid N+1 when rendering album lists with artist names. Filters by `?artist=` and `?release_year=`. |
| `tracks(request, pk)` | Returns tracks in this album ordered by `disc_number` then `track_number` — the canonical playback order. |
| `new_releases(request)` | Returns 20 most recently released albums. Used for "New This Week" features. |

---

### Playlist App

#### `playlist/models.py`

**`Playlist`** — `owner` (FK User), `track_list` (M2M Track), `collaborators` (M2M User), `is_public` (bool). Indexed on `(owner, -updated_at)` and `(is_public, -updated_at)` for fast personal and public playlist queries.

- `track_count` (property) — `self.track_list.count()`. Displayed in playlist cards.
- `total_duration` (property) — Aggregate `Sum('duration')` across all tracks. Displayed in playlist detail pages.

#### `playlist/serializers.py`

**`PlaylistDetailSerializer`**
- `get_tracks(obj)` — Returns the first 50 available tracks. This cap prevents accidentally transferring thousands of track objects in a single response for very large playlists.
- `get_total_duration(obj)` — Formatted total duration.

**`PlaylistListSerializer`** — Excludes the track list entirely (expensive M2M join), returning only metadata and `track_count`. Essential for performance when a user has many playlists.

#### `playlist/views.py`

**`PlaylistViewSet`**

| Method | Description |
|--------|-------------|
| `get_queryset()` | Authenticated users see their own playlists + all public playlists. Unauthenticated users see only public playlists. Prevents private playlist leakage. |
| `perform_create(serializer)` | Injects `owner=request.user` into the serializer's `save()` call so the client never needs to send their own user ID. |
| `add_tracks(request, pk)` | Accepts `{"track_ids": [1, 2, 3]}` and bulk-adds tracks to the playlist. Only accessible to owner or collaborators (enforced by `CanManagePlaylist`). |
| `remove_tracks(request, pk)` | Inverse of `add_tracks`. Removes tracks by ID list. |
| `mine(request)` | Returns current user's playlists only, ordered by last-updated. Used for the user's library view. |

---

### Authentication App

#### `authentication/views.py`

These are **legacy Token-based views** kept for backward compatibility. New clients should use the JWT endpoints at `/api/v1/auth/token/`.

| Function | Description |
|----------|-------------|
| `login(request)` | Looks up user by `username`, checks password with `check_password()`, returns a DRF `Token`. Returns 404 if user not found. |
| `signup(request)` | Creates user via `UserSerializer`, calls `set_password()` to hash the password (the serializer stores it plaintext, so this step is mandatory), creates a Token. Returns 400 on validation error. |
| `test_token(request)` | Protected by `TokenAuthentication` + `IsAuthenticated`. Returns the username — used to verify a token is still valid. |
| `logout(request)` | Deletes the user's `Token` row, invalidating it server-side. JWTs (from the `/api/v1/auth/` endpoints) use a blacklist instead. |

---

### Streaming App

The streaming app implements RFC 7233 HTTP Range Requests — the standard that allows audio players to seek without re-downloading from the start.

#### `streaming/models.py`

| Model | Purpose |
|-------|---------|
| `PlayHistory` | Records each stream event with user, track, timestamp, context (`web`/`mobile`/`desktop`), and partial `duration_listened`. Powers listening analytics. |
| `StreamSession` | Tracks active streaming sessions per device. Can be used to enforce concurrent stream limits. |
| `UserFavorite` | Simple join table `(user, track)` with a `unique_together` constraint. Powers the "liked songs" library. |
| `UserQueue` | Represents a user's playback queue with `shuffle_enabled` and `repeat_mode` (`off`/`one`/`all`). |
| `QueueTrack` | An individual entry in a `UserQueue` with `position` ordering. |

#### `streaming/views.py`

**`StreamingThrottle`** — Subclasses `UserRateThrottle` with a dedicated `streaming` scope. Keeps streaming rate limits separate from general API rate limits so heavy streamers don't consume their API quota.

**`get_content_type(file_path)`** — Maps file extensions to MIME types (`audio/mpeg`, `audio/ogg`, `audio/flac`, etc.). Correct MIME types tell the browser's `<audio>` element which decoder to use. Falls back to `application/octet-stream` for unknown formats.

**`parse_range_header(range_header, file_size)`**
- Parses `bytes=START-END` format from the `Range` request header.
- Handles three syntaxes: `bytes=500-999` (explicit range), `bytes=500-` (from offset to end), `bytes=-500` (last 500 bytes).
- Returns `(start, end)` tuple or `(None, None)` if the header is absent/malformed.
- This is critical for audio seeking — without proper Range parsing, users cannot skip to the middle of a song.

**`file_iterator(file_path, start, end, chunk_size)`** — Generator function that opens the audio file, seeks to `start`, and yields `chunk_size` bytes at a time until `end`. Streaming in chunks (default 64 KB) prevents loading entire audio files into memory regardless of file size.

**`stream_track(request, track_id)`** — The core streaming view. Full behaviour:
1. Authenticates the request.
2. Fetches the `Track` record.
3. Determines `content_type`.
4. Parses the `Range` header.
5. Returns `416 Range Not Satisfiable` if `start >= file_size`.
6. Returns `206 Partial Content` with `Content-Range: bytes START-END/TOTAL` if a range was requested.
7. Returns `200 OK` with full file if no range was requested.
8. Always includes `Accept-Ranges: bytes` so clients know seeking is supported.
9. Creates a `PlayHistory` record.
10. Atomically increments `play_count`.

**`get_stream_url(request, track_id)`** — Returns stream metadata: the URL, file size, content type, and available quality variants from `TranscodedTrack`. Used by clients that need to display stream info before initiating playback.

**`get_play_history(request)`** — Returns the authenticated user's play history, paginated, ordered by most recent. Powers the "Recently Played" section.

**`clear_play_history(request)`** — Deletes all `PlayHistory` rows for the current user. A privacy feature — equivalent to "Clear watch history".

---

### Transcoding App

Provides adaptive bitrate streaming by pre-converting audio files into multiple quality variants in the background.

#### `transcoding/models.py`

**`TranscodedTrack`** — Represents one quality variant of a `Track`. Fields: `original_track` (FK), `quality` (`low`/`medium`/`high`/`lossless`), `status` (`pending`/`processing`/`completed`/`failed`), `transcoded_file`, `file_size`, `error_message`. `unique_together = ['original_track', 'quality']` ensures only one variant per quality exists.

#### `transcoding/service.py`

Pure functions wrapping FFmpeg subprocesses. No Django dependencies — can be unit-tested without a database.

| Function | Description |
|----------|-------------|
| `_ffmpeg_bin()` | Resolves the FFmpeg binary path from `settings.FFMPEG_BINARY` or falls back to `shutil.which('ffmpeg')`. Centralises binary detection. |
| `_ffprobe_bin()` | Same for FFprobe. |
| `check_ffmpeg_installed()` | Runs `ffmpeg -version` and returns `True`/`False`. Called at task start to give a clear error instead of a cryptic subprocess crash. |
| `probe_audio(input_path)` | Runs `ffprobe -v quiet -print_format json -show_format -show_streams` and parses the JSON output into a dict with `duration`, `bitrate`, `sample_rate`, `channels`, `codec_name`. Used to populate `Track` metadata fields after upload. |
| `transcode(input_path, output_path, codec, bitrate, sample_rate, channels)` | Runs FFmpeg to convert `input_path` to `output_path` with the specified codec and quality settings. Raises `TranscodingError` on non-zero exit code. Returns the output path on success. |
| `generate_waveform(input_path, num_points)` | Decodes audio to raw PCM, samples at `num_points` intervals, extracts peak amplitude per segment, and normalises to 0.0–1.0. Returns a list of floats that front-ends render as the waveform visualisation bar chart. |

#### `transcoding/tasks.py`

Celery tasks decorated with `@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=60)`.

| Task | Description |
|------|-------------|
| `transcode_track(track_id, quality)` | **Idempotent**: checks for an existing `completed` `TranscodedTrack` before starting — safe to call multiple times. Sets status to `processing`, calls `service.transcode()`, saves the output file, sets status to `completed`. On failure, sets status to `failed` with the error message and raises to trigger a retry. |
| `transcode_all_qualities(track_id)` | Fan-out coordinator: dispatches one `transcode_track` task per quality preset (`low`/`medium`/`high`/`lossless`) using `.delay()`. Decouples the trigger from the actual work. |
| `generate_waveform_task(track_id, num_points)` | Calls `service.generate_waveform()` and persists the result as JSON to `Track.waveform_data`. Front-ends read this field to render the visualisation without re-processing the audio. |
| `probe_and_update_metadata(track_id)` | Calls `service.probe_audio()` and updates `Track.bitrate`, `Track.sample_rate`, `Track.channels`, `Track.duration` from the FFprobe output. Runs automatically after a track is uploaded. |

#### `transcoding/views.py`

All views require admin (`IsAdminOrReadOnly`).

| Function | Description |
|----------|-------------|
| `list_variants(request, track_id)` | Returns all `completed` `TranscodedTrack` variants for a given track. Clients call this to discover available quality options before streaming. |
| `trigger_transcode(request, track_id)` | Accepts `{"quality": "high"}` and dispatches `transcode_track.delay()` for that single quality. |
| `trigger_transcode_all(request, track_id)` | Dispatches `transcode_all_qualities.delay()`. The response returns immediately with `202 Accepted`; the actual work happens asynchronously. |
| `trigger_waveform(request, track_id)` | Dispatches `generate_waveform_task.delay()`. |

---

### Search App

#### `search/views.py`

**`_es_available()`** — Checks `settings.ELASTICSEARCH_DSL` for non-empty configuration. This is the single decision point for ES vs ORM mode — no try/except around every query.

**`unified_search(request)`** — Public entry point. Validates all parameters, then routes to `_es_search` or `_orm_search`. Returns `{"tracks": [...], "artists": [...], "albums": [...]}`.

**`autocomplete(request)`** — Returns suggestions for partial queries (minimum 2 characters). Used for real-time search-as-you-type dropdowns. Routes to `_es_autocomplete` or `_orm_autocomplete`.

**`_es_search(query, restrict_type, genre_slug, year_from, year_to, limit)`** — Executes `multi_match` queries with `fuzziness='AUTO'` across denormalized ES fields. `fuzziness='AUTO'` allows 1–2 character typos to still return results. Applies `term` filters for genre and `range` filters for year bounds.

**`_es_autocomplete(query, limit)`** — Uses `match_phrase_prefix` for prefix matching. Deduplicates by `(type, id)` so the same track doesn't appear multiple times. Caps results at `limit`.

**`_orm_search(query, ...)`** — Django ORM equivalent using `Q(field__icontains=query)` chains joined with `|`. Less powerful than ES (no fuzzy matching, no relevance scoring) but always available.

**`_orm_autocomplete(query, limit)`** — Simple `title__icontains` lookups across Track, Artist, Album tables.

#### `search/documents.py`

Elasticsearch document definitions using `django-elasticsearch-dsl`.

**`TrackDocument`** — Maps `Track` fields to an ES index with a custom `autocomplete` analyser (edge n-gram tokeniser). This analyser indexes `"Beatles"` as `["b", "be", "bea", "beat", "beatl", "beatle", "beatles"]`, enabling instant character-by-character matching.

**`get_instances_from_related(related_instance)`** — When a related `Artist`, `Album`, or `Genre` changes, this method tells django-elasticsearch-dsl which `Track` documents to re-index. Without this, changing an artist's name would leave stale data in the ES index.

**`ArtistDocument`** / **`AlbumDocument`** — Similar patterns for their respective models.

---

### Realtime App

#### `realtime/auth.py`

**`get_user_from_token(token_str)`** — Decorated with `@database_sync_to_async` to safely call Django's synchronous ORM from an async context. Validates the JWT `AccessToken` (raises `TokenError` on invalid/expired tokens) and returns the `User` instance.

**`JWTAuthMiddleware.__call__(scope, receive, send)`**
- Parses the `token` query parameter from the WebSocket URL (`?token=<jwt>`).
- Calls `get_user_from_token()` asynchronously.
- Attaches `scope['user']` for the consumer to read.
- On any failure (missing token, invalid JWT, user not found), passes `AnonymousUser` — the consumer then closes with code `4001`.

WebSocket connections cannot send custom HTTP headers after the initial handshake, which is why JWT is passed as a query parameter rather than `Authorization: Bearer`.

#### `realtime/consumers.py`

**`NotificationConsumer`** — Per-user WebSocket channel. Every authenticated user gets a private Channel Groups group named `user_{user_id}`.

| Method | Description |
|--------|-------------|
| `connect()` | Accepts the connection and joins the user-specific group. Rejects anonymous connections with close code `4001`. |
| `disconnect(close_code)` | Removes the channel from the group, cleaning up so broadcast messages don't attempt delivery to a closed socket. |
| `receive_json(content)` | Handles inbound messages from the client. Currently responds to `{"type": "ping"}` with `{"type": "pong"}` — a keep-alive mechanism. |
| `notification(event)` | Generic handler for server-push notifications. Called by the Channel layer when `group_send` targets this consumer's group. |
| `track_released(event)` | Specialised handler called when a new track is uploaded. Pushes track metadata to the user's client. |
| `playlist_updated(event)` | Called when a collaborative playlist is modified. Pushes the change to all connected collaborators. |
| `now_playing(event)` | Called when a followed user starts playing a track. |

**`NowPlayingConsumer`** — Global broadcast channel. All connected authenticated users join a single `now_playing` group.

| Method | Description |
|--------|-------------|
| `connect()` / `disconnect()` | Standard group join/leave. |
| `receive_json(content)` | Handles `{"type": "update", "track_id": 123}` from a client. Broadcasts to the entire `now_playing` group so all connected users see who's listening to what. |
| `now_playing(event)` | Delivers the broadcast payload to each connected client. |

#### `realtime/signals.py`

Django signals that bridge synchronous ORM events to async Channel layer messages.

- `notify_new_track` — Connected to `post_save` on `Track`. When `created=True`, sends a `track_released` event to the uploading user's notification group.
- `broadcast_now_playing` — Connected to `post_save` on `PlayHistory`. When a new play history entry is created, broadcasts the now-playing event to the global group.

---

## API Endpoints

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/token/` | Obtain JWT access + refresh tokens |
| POST | `/api/v1/auth/token/refresh/` | Exchange refresh token for new access token |
| POST | `/api/v1/auth/token/verify/` | Verify a token is valid |
| POST | `/api/v1/auth/register/` | Register new user account |

### Tracks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tracks/` | Paginated track list (cached 5 min) |
| POST | `/api/v1/tracks/` | Upload new track (admin) |
| GET | `/api/v1/tracks/{id}/` | Full track detail + stream URL |
| PUT/PATCH | `/api/v1/tracks/{id}/` | Update track metadata (admin) |
| DELETE | `/api/v1/tracks/{id}/` | Remove track (admin) |
| GET | `/api/v1/tracks/top/` | Most-played tracks |
| GET | `/api/v1/tracks/recent/` | Most recently added tracks |
| POST | `/api/v1/tracks/{id}/play/` | Increment play count, returns new count |

### Genres / Artists / Albums

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/genres/` | All genres with track counts |
| GET | `/api/v1/genres/{slug}/` | Genre detail |
| GET | `/api/v1/genres/{slug}/tracks/` | Paginated tracks in genre |
| GET | `/api/v1/artists/` | Paginated artists |
| GET | `/api/v1/artists/{id}/` | Artist detail + stats |
| GET | `/api/v1/artists/{id}/tracks/` | Tracks by artist |
| GET | `/api/v1/artists/{id}/albums/` | Albums by artist |
| GET | `/api/v1/albums/` | Paginated albums |
| GET | `/api/v1/albums/{id}/` | Album detail + tracks |

### Playlists

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/playlists/` | Public + own playlists |
| POST | `/api/v1/playlists/` | Create playlist |
| GET | `/api/v1/playlists/mine/` | Current user's playlists only |
| GET/PUT | `/api/v1/playlists/{id}/` | Retrieve or update playlist |
| DELETE | `/api/v1/playlists/{id}/` | Delete (owner only) |
| POST | `/api/v1/playlists/{id}/add_tracks/` | Add tracks by ID list |
| POST | `/api/v1/playlists/{id}/remove_tracks/` | Remove tracks by ID list |

### Streaming

| Method | Path | Description |
|--------|------|-------------|
| GET/HEAD | `/api/v1/stream/{id}/` | Stream audio (supports Range header) |
| GET | `/api/v1/stream/url/{id}/` | Stream metadata + quality variants |
| GET | `/api/v1/stream/history/` | Play history (paginated) |
| DELETE | `/api/v1/stream/history/` | Clear all play history |
| GET | `/api/v1/stream/favorites/` | User's favourites |
| POST | `/api/v1/stream/favorites/{id}/` | Add to favourites |
| DELETE | `/api/v1/stream/favorites/{id}/` | Remove from favourites |

### Transcoding

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/transcode/{id}/variants/` | List completed quality variants |
| POST | `/api/v1/transcode/{id}/transcode/` | Queue single-quality transcode (admin) |
| POST | `/api/v1/transcode/{id}/transcode/all/` | Queue all qualities (admin) |
| POST | `/api/v1/transcode/{id}/waveform/` | Queue waveform generation (admin) |

### Search

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/search/?q=<query>` | Search tracks, artists, albums |
| GET | `/api/v1/search/autocomplete/?q=<q>` | Typeahead suggestions |

### WebSocket

| URL | Description |
|-----|-------------|
| `ws://host/ws/notifications/?token=<jwt>` | Per-user notification stream |
| `ws://host/ws/now-playing/` | Global now-playing broadcast |

### Docs

| URL | Description |
|-----|-------------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | Raw OpenAPI JSON |
| `/health/` | Health check |

---

## Running Locally

```bash
# 1. Clone the repository
git clone <repo-url>
cd Spotifylookalike

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Open .env and set at minimum:
#   DJANGO_SECRET_KEY=<random-string>
#   DJANGO_DEBUG=True

# 5. Run database migrations
python manage.py migrate

# 6. Create an admin user
python manage.py createsuperuser

# 7. Start the API server
python manage.py runserver

# 8. (Optional) Start the Celery worker for transcoding
celery -A spotify worker -l info

# 9. (Optional) Start the WebSocket server
daphne -b 0.0.0.0 -p 8001 spotify.asgi:application
```

Once running:
- API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/api/docs/`
- Admin: `http://localhost:8000/admin/`

---

## Docker Deployment

```bash
# Copy and configure environment file
cp .env.example .env
# Edit .env with production secrets

# Start all 8 services
docker-compose up -d

# Apply database migrations
docker-compose exec web python manage.py migrate

# Create admin user
docker-compose exec web python manage.py createsuperuser

# View logs
docker-compose logs -f web
docker-compose logs -f celery
```

**Services started by Docker Compose:**

| Service | Port | Role |
|---------|------|------|
| `nginx` | 80 | Reverse proxy, WebSocket routing |
| `web` | 8000 | Gunicorn HTTP API |
| `websocket` | 8001 | Daphne WebSocket server |
| `db` | 5432 | PostgreSQL |
| `redis` | 6379 | Cache + Celery broker + Channel layer |
| `celery` | — | Celery transcoding worker |
| `celery-beat` | — | Scheduled task runner |
| `elasticsearch` | 9200 | Search index |

---

## Running Tests

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Run the full test suite
pytest

# Run with coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Run a specific module
pytest tests/test_streaming.py -v

# Run a single test
pytest tests/test_permissions.py::TestIsAdminOrReadOnly::test_admin_can_write -v
```

**Test files and their coverage:**

| File | What it tests |
|------|---------------|
| `tests/test_models.py` | Model field defaults, constraints, properties, `__str__` |
| `tests/test_api.py` | CRUD endpoints, authentication, pagination, filtering |
| `tests/test_streaming.py` | Range parsing, 206/416 responses, play history, play count |
| `tests/test_transcoding.py` | FFmpeg service, Celery tasks, idempotency, error handling |
| `tests/test_search.py` | ORM fallback search, type/genre/year filters, autocomplete |
| `tests/test_realtime.py` | WebSocket connect/disconnect, JWT rejection, broadcasts |
| `tests/test_permissions.py` | All permission classes at unit and API level |
| `tests/test_serializers.py` | File size validation, computed fields, field exclusions |
