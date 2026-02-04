from django.urls import path
from . import views

app_name = 'transcoding'

urlpatterns = [
    path('<int:track_id>/variants/', views.list_variants, name='list-variants'),
    path('<int:track_id>/transcode/', views.trigger_transcode, name='trigger-transcode'),
    path('<int:track_id>/transcode/all/', views.trigger_transcode_all, name='trigger-transcode-all'),
    path('<int:track_id>/waveform/', views.trigger_waveform, name='trigger-waveform'),
]
