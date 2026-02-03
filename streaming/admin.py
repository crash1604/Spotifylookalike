from django.contrib import admin
from .models import PlayHistory, StreamSession, UserFavorite, UserQueue, QueueTrack


@admin.register(PlayHistory)
class PlayHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'track', 'played_at', 'completed', 'context']
    list_filter = ['completed', 'context', 'played_at']
    search_fields = ['user__username', 'track__title']
    date_hierarchy = 'played_at'
    raw_id_fields = ['user', 'track']


@admin.register(StreamSession)
class StreamSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'track', 'quality', 'is_active', 'started_at']
    list_filter = ['is_active', 'quality', 'device_type']
    search_fields = ['user__username', 'session_id']
    raw_id_fields = ['user', 'track']


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'track', 'created_at']
    search_fields = ['user__username', 'track__title']
    raw_id_fields = ['user', 'track']


@admin.register(UserQueue)
class UserQueueAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_track', 'current_position', 'shuffle', 'repeat_mode']
    raw_id_fields = ['user', 'current_track']


@admin.register(QueueTrack)
class QueueTrackAdmin(admin.ModelAdmin):
    list_display = ['queue', 'track', 'position', 'added_at']
    list_filter = ['added_at']
    raw_id_fields = ['queue', 'track']
