from django.urls import path
from .views import (
    add_track,
    track_detail_page,
    delete_track,
    update_track,

)

urlpatterns = [
    path('<int:track_id>/', track_detail_page),
    path('add/', add_track),
    path('<int:track_id>/delete', delete_track),
    path('<int:track_id>/update', update_track),

]