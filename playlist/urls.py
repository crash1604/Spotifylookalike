from django.urls import path
from . import views

urlpatterns = [
    path('',views.get_all_playlists, name='get_all_playlists'),
    path('<str:playlist_name>/', views.get_playlist_by_name, name='get_playlist_by_name')
    
]
