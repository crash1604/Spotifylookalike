from django.urls import path
from . import views

urlpatterns = [
    # path for get requests
    path('',views.get_all_tracks, name='get_all_tracks'),
    path('add/', views.add_track),
    path('<str:track_name>/delete/', views.delete_track, name='delete_track'),
    path('<str:track_name>/update/', views.update_track, name='update_track'),
    path('<str:track_name>/', views.get_tracks_by_name, name='get_tracks_by_name'),
    
    

]
