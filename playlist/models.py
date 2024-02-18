from django.db import models

# Create your models here.
from django.db import models
from django.apps import apps
from django.contrib.auth.models import User
from music.models import Track

# Create your models here.
class Playlist(models.Model):
    title = models.CharField(max_length=200, unique=True)
    creation_date = models.DateField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    cover_art = models.ImageField(upload_to='albums/', blank=True, null=True)
    track_list= models.ManyToManyField(Track)
    # Add other Playlist-related fields (e.g., record label, producer)
    def __str__(self):
        return self.title