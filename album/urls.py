from django.urls import path
from . import views

urlpatterns = [
    path('',views.get_all_albums, name='get_all_albums'),
    # path('add/',views.add_new_album, name='add_new_album'),
    path('<str:artist_name>/<str:album_name>/', views.get_album_by_artist_and_name, name='get_album_by_artist_and_name'),
    path('<str:artist_name>/', views.get_album_by_artist, name='get_album_by_artist')
    
    
]
