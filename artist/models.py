"""
Artist models.
"""

from django.db import models


class Artist(models.Model):
    """
    Music artist or band.
    """
    name = models.CharField(max_length=100, unique=True, db_index=True)
    biography = models.TextField(blank=True)
    genres = models.ManyToManyField('music.Genre', related_name='artists', blank=True)
    image = models.ImageField(upload_to='artists/', blank=True, null=True)

    # Social links
    website = models.URLField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Verification status
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    @property
    def total_tracks(self):
        return self.tracks.count()

    @property
    def total_albums(self):
        return self.album_set.count()
