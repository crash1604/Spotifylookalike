from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.unified_search, name='unified-search'),
    path('autocomplete/', views.autocomplete, name='autocomplete'),
]
