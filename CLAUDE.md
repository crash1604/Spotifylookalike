# CLAUDE.md – LookALike Project Guide

This file helps AI assistants understand the LookALike codebase, conventions, and workflows.

---

## Project Overview

**LookALike** is a production-ready Django REST Framework backend for a music streaming service.

**Tech stack:**
- **Django 4.x** + **Django REST Framework** – HTTP API
- **Django Channels** + **Daphne** – WebSocket / real-time notifications
- **Celery** + **Redis** – Background tasks (transcoding, etc.)
- **Elasticsearch** (optional) – Full-text search with ORM fallback
- **PostgreSQL** – Primary database (SQLite for local dev)
- **Redis** – Caching, session storage, Celery broker, Channels layer
- **FFmpeg** – Audio transcoding and waveform generation
- **SimpleJWT** – JWT authentication with token rotation and blacklist
- **drf-spectacular** – OpenAPI 3 / Swagger documentation
- **Docker Compose** – Full-stack containerisation (8 services)

---

## Directory Structure

```
LookALike/
│
├── spotify/                # Django project package
│   ├── settings.py         # All configuration (env-var driven)
│   ├── urls.py             # Root URL routing – /api/v1/ + legacy
│   ├── asgi.py             # ASGI app: HTTP + WebSocket (Channels)
│   └── wsgi.py             # WSGI app: gunicorn entrypoint
│
├── core/                   # Shared utilities (no models)
│   ├── permissions.py      # Custom DRF permission classes
│   ├── pagination.py       # Standard / Large / Cursor pagination
│   ├── exceptions.py       # Custom exception classes
│   ├── middleware.py       # Request logging middleware
│   └── logging.py          # JSON logging helpers
│
├── music/                  # Tracks and genres
├── artist/                 # Artist profiles
├── album/                  # Albums
├── playlist/               # User playlists (owner + collaborators)
├── authentication/         # JWT auth + legacy token views
├── streaming/              # Audio streaming (HTTP Range) + history
├── transcoding/            # FFmpeg-based audio transcoding (Celery)
├── search/                 # Elasticsearch search + ORM fallback
├── realtime/               # WebSocket consumers (Django Channels)
│
├── tests/                  # All tests live here
│   ├── factories.py        # factory_boy model factories
│   ├── conftest.py         # pytest fixtures
│   ├── test_models.py      # Unit tests for models
│   ├── test_api.py         # Integration tests for API endpoints
│   ├── test_streaming.py   # Streaming / Range-request tests
│   ├── test_transcoding.py # Celery task / FFmpeg tests
│   ├── test_search.py      # Search (ORM fallback + ES mock) tests
│   ├── test_realtime.py    # WebSocket consumer tests
│   ├── test_permissions.py # Permission class tests
│   └── test_serializers.py # Serializer validation tests
│
├── nginx/conf.d/           # Nginx reverse proxy config
│   └── default.conf        # HTTP + WebSocket proxy, static files
│
├── Dockerfile              # Multi-stage production image (ffmpeg included)
├── docker-compose.yml      # 8 services: web, db, redis, celery, celery-beat,
│                           #   elasticsearch, websocket, nginx
├── requirements.txt        # Python dependencies
├── pytest.ini              # pytest config (DJANGO_SETTINGS_MODULE)
├── .env.example            # All environment variables with defaults
└── .gitignore
```

---

## Django Apps and Responsibilities

| App | Models | Key Views / Tasks |
|-----|--------|-------------------|
| `music` | `Track`, `Genre` | `TrackViewSet`, `GenreViewSet` |
| `artist` | `Artist` | `ArtistViewSet` |
| `album` | `Album` | `AlbumViewSet` |
| `playlist` | `Playlist` | `PlaylistViewSet` (+ add/remove tracks, mine) |
| `authentication` | – | JWT token endpoints + legacy login/signup |
| `streaming` | `PlayHistory`, `StreamSession`, `UserFavorite`, `UserQueue` | `stream_track`, `get_play_history` |
| `transcoding` | `TranscodedTrack` | `transcode_track` (Celery), `generate_waveform_task` |
| `search` | – | `unified_search`, `autocomplete` |
| `realtime` | – | `NotificationConsumer`, `NowPlayingConsumer` (WS) |
| `core` | – | Permissions, pagination, exceptions, middleware |

---

## API Endpoints

### Authentication (`/api/v1/auth/`)
```
POST  /api/v1/auth/token/          Obtain JWT access + refresh tokens
POST  /api/v1/auth/token/refresh/  Refresh access token
POST  /api/v1/auth/token/verify/   Verify a token
POST  /api/v1/auth/register/       Register new user
POST  /api/v1/auth/login/          Legacy token login
POST  /api/v1/auth/logout/         Legacy token logout
```

### Music (`/api/v1/`)
```
GET/POST  /api/v1/tracks/                   List / create tracks
GET       /api/v1/tracks/{id}/              Track detail
PUT/PATCH /api/v1/tracks/{id}/              Update track (admin)
DELETE    /api/v1/tracks/{id}/              Delete track (admin)
GET       /api/v1/tracks/top/               Top played tracks
GET       /api/v1/tracks/recent/            Recently added tracks
GET       /api/v1/tracks/{id}/play/         Increment play count

GET       /api/v1/genres/                   List genres
GET       /api/v1/genres/{slug}/            Genre detail
GET       /api/v1/genres/{slug}/tracks/     Tracks in genre

GET       /api/v1/artists/                  List artists
GET       /api/v1/artists/{id}/             Artist detail

GET       /api/v1/albums/                   List albums
GET       /api/v1/albums/{id}/              Album detail

GET/POST  /api/v1/playlists/                List / create playlists
GET       /api/v1/playlists/mine/           Current user's playlists
GET/PUT   /api/v1/playlists/{id}/           Retrieve / update
DELETE    /api/v1/playlists/{id}/           Delete (owner only)
POST      /api/v1/playlists/{id}/add_tracks/     Add tracks
POST      /api/v1/playlists/{id}/remove_tracks/  Remove tracks
```

### Streaming (`/api/v1/stream/`)
```
GET/HEAD  /api/v1/stream/{track_id}/        Stream audio (Range requests → 206)
GET       /api/v1/stream/url/{track_id}/    Stream URL + metadata
GET       /api/v1/stream/history/           User play history
DELETE    /api/v1/stream/history/           Clear play history
GET       /api/v1/stream/favorites/         User favourites
POST      /api/v1/stream/favorites/{id}/    Add favourite
DELETE    /api/v1/stream/favorites/{id}/    Remove favourite
```

### Transcoding (`/api/v1/transcode/`)
```
GET   /api/v1/transcode/{id}/variants/     List transcoded variants
POST  /api/v1/transcode/{id}/transcode/    Trigger single quality (admin)
POST  /api/v1/transcode/{id}/transcode/all/ Trigger all qualities (admin)
POST  /api/v1/transcode/{id}/waveform/     Trigger waveform generation (admin)
```

### Search (`/api/v1/search/`)
```
GET  /api/v1/search/?q=<query>             Unified multi-model search
GET  /api/v1/search/autocomplete/?q=<q>    Typeahead suggestions
```

### WebSocket
```
ws://host/ws/notifications/?token=<jwt>   Per-user notifications
ws://host/ws/now-playing/                 Global now-playing broadcast
```

### Docs / Utility
```
GET  /api/docs/           Swagger UI
GET  /api/redoc/          ReDoc
GET  /api/schema/         OpenAPI JSON schema
GET  /health/             Health check
```

---

## Environment Variables

Copy `.env.example` to `.env` before running locally.

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DJANGO_SECRET_KEY` | Yes | – | Must be changed in production |
| `DJANGO_DEBUG` | No | `False` | Set `True` for local dev |
| `DJANGO_ALLOWED_HOSTS` | Yes | – | Comma-separated |
| `DATABASE_ENGINE` | No | `sqlite` | Use `django.db.backends.postgresql` for Postgres |
| `DATABASE_NAME` | No | `spotify_db` | |
| `DATABASE_USER` | No | `spotify_user` | |
| `DATABASE_PASSWORD` | No | `` | |
| `DATABASE_HOST` | No | `localhost` | |
| `DATABASE_PORT` | No | `5432` | |
| `REDIS_URL` | No | `redis://localhost:6379/0` | |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/1` | |
| `ELASTICSEARCH_URL` | No | `http://localhost:9200` | Search works without it (ORM fallback) |
| `USE_S3` | No | `False` | AWS S3 for media storage |
| `AWS_ACCESS_KEY_ID` | If S3 | – | |
| `AWS_SECRET_ACCESS_KEY` | If S3 | – | |
| `AWS_STORAGE_BUCKET_NAME` | If S3 | – | |
| `CORS_ALLOWED_ORIGINS` | No | – | Comma-separated |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | No | `60` | |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | No | `7` | |
| `THROTTLE_ANON_RATE` | No | `100/hour` | |
| `THROTTLE_USER_RATE` | No | `1000/hour` | |
| `LOG_LEVEL` | No | `INFO` | |
| `FFMPEG_BINARY` | No | auto-detected | Path to ffmpeg |
| `FFPROBE_BINARY` | No | auto-detected | Path to ffprobe |

---

## Local Development Setup

```bash
# 1. Clone and create virtual environment
git clone <repo> && cd LookALike
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: set DJANGO_SECRET_KEY, DJANGO_DEBUG=True, etc.

# 4. Run migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Start Django dev server
python manage.py runserver

# 7. Start Celery worker (in separate terminal)
celery -A spotify worker -l info

# 8. Start Celery beat scheduler (in separate terminal)
celery -A spotify beat -l info

# 9. Start WebSocket server (optional, in separate terminal)
daphne -b 0.0.0.0 -p 8001 spotify.asgi:application
```

---

## Docker Deployment

```bash
# Start all 8 services
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f celery

# Run migrations inside container
docker-compose exec web python manage.py migrate

# Create superuser inside container
docker-compose exec web python manage.py createsuperuser

# Rebuild after code changes
docker-compose build web && docker-compose up -d web

# Stop everything
docker-compose down
```

**Docker services:**

| Service | Image | Port | Role |
|---------|-------|------|------|
| `web` | app Dockerfile | 8000 | Gunicorn WSGI (HTTP API) |
| `db` | postgres:15 | 5432 | PostgreSQL database |
| `redis` | redis:7 | 6379 | Cache + Celery broker |
| `celery` | app Dockerfile | – | Celery worker |
| `celery-beat` | app Dockerfile | – | Scheduled task runner |
| `elasticsearch` | elasticsearch:8.12 | 9200 | Full-text search |
| `websocket` | app Dockerfile | 8001 | Daphne ASGI (WebSocket) |
| `nginx` | nginx:alpine | 80/443 | Reverse proxy |

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run a specific test file
pytest tests/test_streaming.py -v

# Run a specific test class or function
pytest tests/test_api.py::TestTrackAPI::test_list_tracks -v

# Run with verbose output
pytest -v

# Skip slow tests
pytest -m "not slow"
```

**pytest configuration** (`pytest.ini`):
- `DJANGO_SETTINGS_MODULE = spotify.settings`
- Test paths: `tests/`

**Fixtures** (from `tests/conftest.py`):
- `api_client` – unauthenticated APIClient
- `user`, `admin_user`, `other_user` – User instances
- `authenticated_client`, `admin_client` – pre-credentialed APIClients
- `genre`, `genres`, `artist`, `artists`, `album`, `albums`, `track`, `tracks`
- `playlist`, `playlists`, `sample_audio_file`, `large_dataset`
- `mock_ffmpeg` – patches `transcoding.service.subprocess.run` (simulates FFmpeg success)
- `mock_ffprobe` – patches subprocess.run to return fake audio metadata JSON
- `mock_elasticsearch` – patches ES document `search()` to avoid needing a live cluster

**Factories** (from `tests/factories.py`):
`UserFactory`, `GenreFactory`, `ArtistFactory`, `AlbumFactory`, `TrackFactory`,
`PlaylistFactory`, `PlayHistoryFactory`, `UserFavoriteFactory`,
`TranscodedTrackFactory`, `StreamSessionFactory`

---

## Key Architectural Patterns

### 1. Three-Tier Serializer Pattern
Every resource has three serializers selected by action:

```python
def get_serializer_class(self):
    if self.action == 'list':
        return TrackListSerializer        # Minimal fields, fast
    if self.action in ['create', 'update', 'partial_update']:
        return TrackCreateUpdateSerializer  # Write validation only
    return TrackDetailSerializer          # Full fields + computed properties
```

### 2. ViewSet + DRF Router
All major resources use `ModelViewSet` registered with the DRF router:

```python
router.register(r'tracks', TrackViewSet, basename='track')
```
Avoid adding manual URL entries for standard CRUD – let the router handle it.

### 3. Permission Class Hierarchy
Use the classes from `core/permissions.py`:

| Class | When to use |
|-------|-------------|
| `IsAdminOrReadOnly` | Content only admins should write (tracks, albums) |
| `IsOwnerOrReadOnly` | User-owned resources (playlists) |
| `IsOwner` | Strict ownership (history, queue) |
| `CanManagePlaylist` | Playlist with collaborators |

### 4. Pagination Variants (`core/pagination.py`)
| Class | Page size | Max | Use for |
|-------|-----------|-----|---------|
| `StandardResultsSetPagination` | 20 | 100 | Default |
| `LargeResultsSetPagination` | 50 | 200 | Search results |
| `TrackCursorPagination` | 20 | – | Infinite scroll |

### 5. Celery Tasks (transcoding)
- Tasks are **idempotent**: check for existing `completed` record before doing work.
- Use `autoretry_for=(Exception,)` with `max_retries=3` and `retry_backoff=60`.
- Fan-out pattern: `transcode_all_qualities` dispatches individual `transcode_track` tasks.

### 6. HTTP Range Streaming
`streaming/views.py::stream_track` implements RFC 7233:
- Returns `206 Partial Content` with `Content-Range` when `Range` header present.
- Returns `416 Range Not Satisfiable` when start ≥ file size.
- Returns `200` for full-file requests.
- Always includes `Accept-Ranges: bytes` and `Content-Length`.

### 7. Search with ORM Fallback
`search/views.py::unified_search` checks `_es_available()` first.
- If Elasticsearch is unreachable/unconfigured → falls back to ORM `icontains` queries.
- Never raises a 500 due to missing Elasticsearch.

### 8. WebSocket Auth
JWT is passed as `?token=<jwt>` query parameter (WebSocket connections cannot send headers).
`realtime/auth.py::JWTAuthMiddleware` validates the token and attaches the user to `scope`.
Unauthenticated connections are closed with code `4001`.

---

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Model fields | `snake_case` | `play_count`, `is_available` |
| Boolean fields | `is_<property>` | `is_verified`, `is_public` |
| Timestamp fields | `created_at`, `updated_at` | auto_now_add / auto_now |
| Serializers | `{Model}ListSerializer`, `{Model}DetailSerializer`, `{Model}CreateUpdateSerializer` | `TrackListSerializer` |
| ViewSets | `{Model}ViewSet` | `PlaylistViewSet` |
| Function-based views | `{action}_{resource}` | `stream_track`, `get_play_history` |
| Celery tasks | `{action}_{resource}` | `transcode_track`, `generate_waveform_task` |
| URL names | `{resource}-{action}` (DRF default) | `track-list`, `track-detail` |
| Test classes | `Test{Resource}{Category}` | `TestTrackAPI`, `TestStreamingRangeRequests` |

---

## Model Conventions

Every model should follow this pattern:

```python
class Meta:
    ordering = ['-created_at']
    indexes = [
        models.Index(fields=['field_used_in_filter']),
    ]

# Timestamps on every model
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)

# Boolean flags use is_ prefix
is_available = models.BooleanField(default=True)
```

ForeignKey fields used in filtering queries must have a corresponding entry in `Meta.indexes`.

---

## Common Development Tasks

### Add a track (authenticated)
```bash
curl -X POST http://localhost:8000/api/v1/tracks/ \
  -H "Authorization: Bearer <token>" \
  -F "title=My Song" -F "artist=1" -F "duration=00:03:30" \
  -F "audio_file=@/path/to/song.mp3"
```

### Stream a track with seeking
```bash
# Full file
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/stream/1/

# Bytes 500–999 only
curl -H "Authorization: Bearer <token>" -H "Range: bytes=500-999" \
  http://localhost:8000/api/v1/stream/1/
```

### Trigger transcoding
```bash
curl -X POST http://localhost:8000/api/v1/transcode/1/transcode/all/ \
  -H "Authorization: Bearer <token>"
```

### Search
```bash
curl "http://localhost:8000/api/v1/search/?q=beatles&type=track&genre=rock" \
  -H "Authorization: Bearer <token>"
```

### Connect to WebSocket (JavaScript)
```javascript
const ws = new WebSocket(`ws://localhost:8001/ws/notifications/?token=${jwtToken}`);
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

---

## Production Checklist

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Generate a strong `DJANGO_SECRET_KEY`
- [ ] Set `DJANGO_ALLOWED_HOSTS`
- [ ] Configure PostgreSQL credentials
- [ ] Configure Redis URL
- [ ] Set `USE_S3=True` and configure AWS credentials (or configure another storage backend)
- [ ] Set `ELASTICSEARCH_URL`
- [ ] Configure `CORS_ALLOWED_ORIGINS`
- [ ] Set up HTTPS and update nginx config to uncomment the SSL server block
- [ ] Configure email settings for password reset
- [ ] Set up Sentry (`SENTRY_DSN`) for error tracking
- [ ] Configure regular database backups
- [ ] Change all default passwords in docker-compose.yml

---

## Known Limitations / Technical Debt

- **PlayHistory duration tracking**: `duration_listened` and `completed` fields in `streaming.PlayHistory` are created but not populated by `stream_track()`. The view would need a client-side progress-reporting endpoint or a separate `heartbeat` endpoint.
- **Legacy endpoints**: `authentication/views.py`, and function-based views in music/artist/album/playlist apps are kept for backward compatibility but are not tested and have inconsistent error response formats. Specifically `signup()` returns HTTP 200 on validation error instead of 400.
- **Elasticsearch security**: `xpack.security.enabled=false` in docker-compose.yml is suitable only for internal/dev networks. Enable authentication for internet-facing deployments.
- **collectstatic in Dockerfile**: `RUN python manage.py collectstatic --noinput` at image build time can fail if the database is not available. Move to an entrypoint script if this becomes an issue.
- **Transcoding quality serving**: `stream_track()` always serves the original audio file. The `TranscodedTrack` variants are stored but the streaming endpoint does not yet serve them based on the `?quality=` query param.
