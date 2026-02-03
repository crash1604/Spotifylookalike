"""
Playlist models.
"""

from django.db import models
from django.contrib.auth.models import User
from music.models import Track


class Playlist(models.Model):
    """
    User-created playlist.
    """
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    creation_date = models.DateField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    cover_art = models.ImageField(upload_to='playlists/%Y/%m/', blank=True, null=True)
    track_list = models.ManyToManyField(Track, blank=True, related_name='playlists')

    # Visibility
    is_public = models.BooleanField(default=False)

    # Collaborative playlist support
    collaborators = models.ManyToManyField(
        User,
        blank=True,
        related_name='collaborative_playlists'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['is_public', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.title} by {self.owner.username}"

    @property
    def track_count(self):
        return self.track_list.count()

    @property
    def total_duration(self):
        from django.db.models import Sum
        return self.track_list.aggregate(total=Sum('duration'))['total']
