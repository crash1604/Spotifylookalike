from django.db import models
from django.apps import apps

# Create your models here.
class Album(models.Model):
    title = models.CharField(max_length=200, unique=True)
    release_date = models.DateField()
    artist = models.ForeignKey('artist.Artist', on_delete=models.CASCADE)
    cover_art = models.ImageField(upload_to='albums/', blank=True, null=True)
    # Add other album-related fields (e.g., record label, producer)

    def __str__(self):
        return self.title