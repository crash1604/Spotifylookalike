from django.urls import path
from . import views

urlpatterns = [
    path('',views.get_all_albums, name='get_all_albums'),
    path('<str:album_name>/', views.get_album_by_name, name='get_album_by_name'),
    path('artist/<str:artist_name>', views.get_album_by_artist, name='get_album_by_artist')
    # path('<str:track_name>/', views.get_tracks_by_name, name='get_tracks_by_name'),
    # path('artists/', views.get_artists, name="get_all_artists"),
    # path('artist/<str:artist_name>/', views.get_tracks_by_artist_name, name='get_tracks_by_artist_name'),
    # path('genre/<str:genre>/', views.get_tracks_by_genre, name='get_tracks_by_genre'),
    # path('album/<str:album_name>/', views.get_tracks_by_album, name='get_tracks_by_album'),
    
    
]
