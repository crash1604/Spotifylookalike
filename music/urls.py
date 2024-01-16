from django.urls import path
from . import views

urlpatterns = [
    path('',views.get_all_tracks, name='get_all_tracks'),
    path('<str:track_name>/', views.get_tracks_by_name, name='get_tracks_by_name'),
    # path('artists/', views.get_artists, name="get_all_artists"),
    # path('artist/<str:artist_name>/', views.get_tracks_by_artist_name, name='get_tracks_by_artist_name'),
    # path('genre/<str:genre>/', views.get_tracks_by_genre, name='get_tracks_by_genre'),
    
    
    
]
