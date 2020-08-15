from django.forms import ModelForm
from music.models import Track
from django.db import models


class MusicEntry(ModelForm):
    class Meta:
        model = Track
        fields = '__all__'
