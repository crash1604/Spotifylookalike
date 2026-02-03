"""
Album models.
"""

from django.db import models


class Album(models.Model):
    """
    Music album.
    """
    title = models.CharField(max_length=200, db_index=True)
    release_date = models.DateField()
    artist = models.ForeignKey('artist.Artist', on_delete=models.CASCADE)
    cover_art = models.ImageField(upload_to='albums/%Y/%m/', blank=True, null=True)

    # Additional metadata
    record_label = models.CharField(max_length=200, blank=True)
    total_tracks = models.PositiveIntegerField(default=0)
    album_type = models.CharField(
        max_length=20,
        choices=[
            ('album', 'Album'),
            ('single', 'Single'),
            ('ep', 'EP'),
            ('compilation', 'Compilation'),
        ],
        default='album'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['artist', 'release_date']),
            models.Index(fields=['-release_date']),
        ]
        unique_together = [['title', 'artist']]

    def __str__(self):
        return f"{self.title} - {self.artist.name}"

    @property
    def duration(self):
        """Calculate total album duration."""
        from django.db.models import Sum
        total = self.tracks.aggregate(total=Sum('duration'))['total']
        return total
