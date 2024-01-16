from django.urls import path
from . import views

urlpatterns = [
    path('',views.get_all_artists, name='get_all_artists'),
    path('<str:artist_name>/', views.get_artist_by_name, name='get_artist_by_name')    
]
