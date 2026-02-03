"""
URL routing for streaming endpoints.
"""

from django.urls import path
from . import views

app_name = 'streaming'

urlpatterns = [
    # Audio streaming
    path('<int:track_id>/', views.stream_track, name='stream-track'),
    path('<int:track_id>/info/', views.get_stream_url, name='stream-info'),

    # Play history
    path('history/', views.get_play_history, name='play-history'),
    path('history/clear/', views.clear_play_history, name='clear-history'),
]
