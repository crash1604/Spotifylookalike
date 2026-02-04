from django.contrib import admin
from .models import TranscodedTrack


@admin.register(TranscodedTrack)
class TranscodedTrackAdmin(admin.ModelAdmin):
    list_display = ['original_track', 'quality', 'codec', 'bitrate', 'status', 'file_size', 'created_at']
    list_filter = ['status', 'quality', 'codec']
    search_fields = ['original_track__title']
    raw_id_fields = ['original_track']
    readonly_fields = ['created_at', 'completed_at']
