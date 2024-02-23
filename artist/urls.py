from django.urls import path
from . import views

urlpatterns = [
    path('',views.get_all_artists, name='get_all_artists'),
    path('add/',views.add_new_artist, name='add_new_artist'),
    path('<str:artist_name>/delete/',views.delete_artist_by_name, name='delete_artist_by_name'),
    path('<str:artist_name>/modify/',views.modify_artist_by_name, name='modify_artist_by_name'),
    path('<str:artist_name>/', views.get_artist_by_name, name='get_artist_by_name'),
]
