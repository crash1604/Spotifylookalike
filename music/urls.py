from django.urls import path
from . import views

urlpatterns = [
    # path for get requests
    path('',views.get_all_tracks, name='get_all_tracks'),
    path('add/', views.add_track),
    path('<str:track_name>/', views.get_tracks_by_name, name='get_tracks_by_name'),
    

]
