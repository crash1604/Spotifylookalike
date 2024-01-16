from django.db import models
from django.apps import apps

class Artist(models.Model):
    name = models.CharField(max_length=100)
    biography = models.TextField(blank=True)
    genres = models.ManyToManyField('music.Genre', related_name='artists', blank=True)
  

    def __str__(self):
        return self.name

