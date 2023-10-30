from django.db import models

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Artist(models.Model):
    name = models.CharField(max_length=100)
    biography = models.TextField(blank=True)
    genres = models.ManyToManyField(Genre, related_name='artists', blank=True)
    # Add other artist-related fields (e.g., date of birth, profile picture)

    def __str__(self):
        return self.name

class Album(models.Model):
    title = models.CharField(max_length=200)
    release_date = models.DateField()
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    cover_art = models.ImageField(upload_to='albums/', blank=True, null=True)
    # Add other album-related fields (e.g., record label, producer)

    def __str__(self):
        return self.title

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
