from django.db import models
from artist.models import Artist
from album.models import Album

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Track(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    duration = models.DurationField()
    release_date = models.DateField()
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to='tracks/')
    # Add other track-related fields (e.g., lyrics)

    def __str__(self):
        return self.title
