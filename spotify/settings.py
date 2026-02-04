"""
Django settings for spotify project - Production Ready Configuration.

Security settings follow Django deployment checklist:
https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# Environment variable helper with type casting
def get_env(key, default=None, cast=str):
    """Get environment variable with type casting support."""
    value = os.environ.get(key, default)
    if value is None:
        return None
    if cast == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    if cast == list:
        return [item.strip() for item in value.split(',') if item.strip()]
    return cast(value)


# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env('DJANGO_SECRET_KEY', 'dev-only-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env('DJANGO_DEBUG', 'False', cast=bool)

ALLOWED_HOSTS = get_env('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1', cast=list)

# Security middleware settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = get_env('SECURE_SSL_REDIRECT', 'True', cast=bool)


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.storage',
    'channels',
    'django_elasticsearch_dsl',

    # Local apps
    'music',
    'authentication',
    'artist',
    'album',
    'playlist',
    'streaming',
    'core',
    'transcoding',
    'search',
    'realtime',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static file serving
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RequestLoggingMiddleware',  # Custom logging middleware
]

ROOT_URLCONF = 'spotify.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'spotify.wsgi.application'
ASGI_APPLICATION = 'spotify.asgi.application'


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Use PostgreSQL for production, SQLite for development
if get_env('DATABASE_ENGINE', 'sqlite'):
    if 'postgresql' in get_env('DATABASE_ENGINE', ''):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': get_env('DATABASE_NAME', 'spotify_db'),
                'USER': get_env('DATABASE_USER', 'spotify_user'),
                'PASSWORD': get_env('DATABASE_PASSWORD', ''),
                'HOST': get_env('DATABASE_HOST', 'localhost'),
                'PORT': get_env('DATABASE_PORT', '5432'),
                'CONN_MAX_AGE': 60,  # Connection pooling
                'OPTIONS': {
                    'connect_timeout': 10,
                },
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# =============================================================================
# CACHING WITH REDIS
# =============================================================================

REDIS_URL = get_env('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    } if not DEBUG else {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Session storage in Redis for production
if not DEBUG:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# AWS S3 Configuration for production media storage
USE_S3 = get_env('USE_S3', 'False', cast=bool)

if USE_S3:
    AWS_ACCESS_KEY_ID = get_env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = get_env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = get_env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = get_env('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_FILE_OVERWRITE = False

    # Use S3 for media files
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'


# =============================================================================
# REST FRAMEWORK CONFIGURATION
# =============================================================================

REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],

    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,

    # Filtering
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    # Throttling (Rate Limiting)
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': get_env('THROTTLE_ANON_RATE', '100/hour'),
        'user': get_env('THROTTLE_USER_RATE', '1000/hour'),
        'streaming': '500/hour',  # Custom rate for streaming
    },

    # Renderers
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ] + (['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []),

    # Schema generation for API documentation
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # Exception handling
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',

    # Versioning
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
}


# =============================================================================
# JWT CONFIGURATION
# =============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=get_env('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '60', cast=int)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=get_env('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7', cast=int)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'TOKEN_OBTAIN_SERIALIZER': 'authentication.serializers.CustomTokenObtainPairSerializer',
}


# =============================================================================
# CORS CONFIGURATION
# =============================================================================

CORS_ALLOWED_ORIGINS = get_env(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000',
    cast=list
)

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'range',  # Important for audio streaming
]

CORS_EXPOSE_HEADERS = [
    'content-length',
    'content-range',
    'accept-ranges',
    'content-type',
]


# =============================================================================
# API DOCUMENTATION (SWAGGER/OPENAPI)
# =============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'Music Streaming API',
    'DESCRIPTION': 'A production-ready API for music streaming services',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v[0-9]',
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication endpoints'},
        {'name': 'Tracks', 'description': 'Track management and streaming'},
        {'name': 'Artists', 'description': 'Artist management'},
        {'name': 'Albums', 'description': 'Album management'},
        {'name': 'Playlists', 'description': 'Playlist management'},
        {'name': 'Streaming', 'description': 'Audio streaming endpoints'},
        {'name': 'User', 'description': 'User profile and preferences'},
    ],
}


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = get_env('LOG_LEVEL', 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'json': {
            '()': 'core.logging.JSONFormatter',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple' if DEBUG else 'json',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'spotify': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'streaming': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}


# =============================================================================
# CELERY CONFIGURATION (ASYNC TASKS)
# =============================================================================

CELERY_BROKER_URL = get_env('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes


# =============================================================================
# STREAMING CONFIGURATION
# =============================================================================

# Audio streaming settings
STREAMING_CHUNK_SIZE = 1024 * 256  # 256 KB chunks for streaming
STREAMING_SUPPORTED_FORMATS = ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg']
STREAMING_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB max file size

# Quality presets for adaptive streaming
STREAMING_QUALITY_PRESETS = {
    'low': {'bitrate': 96, 'format': 'mp3'},
    'medium': {'bitrate': 160, 'format': 'mp3'},
    'high': {'bitrate': 320, 'format': 'mp3'},
    'lossless': {'bitrate': None, 'format': 'flac'},
}


# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' if not DEBUG else 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = get_env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = get_env('EMAIL_PORT', '587', cast=int)
EMAIL_USE_TLS = get_env('EMAIL_USE_TLS', 'True', cast=bool)
EMAIL_HOST_USER = get_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_env('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = get_env('DEFAULT_FROM_EMAIL', 'noreply@spotify.com')


# =============================================================================
# DJANGO CHANNELS (WEBSOCKETS)
# =============================================================================

ASGI_APPLICATION = 'spotify.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [get_env('REDIS_URL', 'redis://localhost:6379/0')],
        },
    } if not DEBUG else {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}


# =============================================================================
# ELASTICSEARCH CONFIGURATION
# =============================================================================

ELASTICSEARCH_DSL = {
    'default': {
        'hosts': get_env('ELASTICSEARCH_URL', 'http://localhost:9200'),
        'timeout': 30,
    },
} if get_env('ELASTICSEARCH_URL') else {}

# Auto-sync models to ES on save/delete
ELASTICSEARCH_DSL_AUTOSYNC = get_env('ELASTICSEARCH_DSL_AUTOSYNC', 'True', cast=bool)
ELASTICSEARCH_DSL_PARALLEL = True


# =============================================================================
# FFMPEG CONFIGURATION (AUDIO TRANSCODING)
# =============================================================================

FFMPEG_BINARY = get_env('FFMPEG_BINARY', 'ffmpeg')
FFPROBE_BINARY = get_env('FFPROBE_BINARY', 'ffprobe')
