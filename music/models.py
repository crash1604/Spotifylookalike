"""
Music models for tracks and genres.
"""

from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from artist.models import Artist
from album.models import Album


class Genre(models.Model):
    """
    Music genre classification.
    """
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Track(models.Model):
    """
    Individual music track.
    """
    title = models.CharField(max_length=200, db_index=True)
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name='tracks'
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='tracks',
        null=True,
        blank=True
    )
    duration = models.DurationField(
        help_text='Track duration in HH:MM:SS format'
    )
    release_date = models.DateField(null=True, blank=True)
    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        related_name='tracks',
        null=True,
        blank=True
    )
    audio_file = models.FileField(
        upload_to='tracks/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg']
            )
        ],
        help_text='Audio file (MP3, WAV, FLAC, AAC, M4A, OGG)'
    )

    # Metadata
    track_number = models.PositiveIntegerField(null=True, blank=True)
    disc_number = models.PositiveIntegerField(default=1)
    explicit = models.BooleanField(default=False)
    lyrics = models.TextField(blank=True)

    # Analytics
    play_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)

    # Audio metadata
    bitrate = models.PositiveIntegerField(null=True, blank=True, help_text='Bitrate in kbps')
    sample_rate = models.PositiveIntegerField(null=True, blank=True, help_text='Sample rate in Hz')
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text='File size in bytes')

    # Waveform data for visualization (JSON array of amplitudes)
    waveform_data = models.JSONField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Availability
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['album', 'disc_number', 'track_number', 'title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['artist', 'title']),
            models.Index(fields=['album', 'track_number']),
            models.Index(fields=['genre']),
            models.Index(fields=['-play_count']),
            models.Index(fields=['-created_at']),
        ]
        # Allow same title for different artists/albums
        unique_together = [['title', 'artist', 'album']]

    def __str__(self):
        return f"{self.title} - {self.artist.name}"

    @property
    def duration_seconds(self):
        """Return duration in seconds."""
        if self.duration:
            return self.duration.total_seconds()
        return 0

    @property
    def formatted_duration(self):
        """Return duration in MM:SS or HH:MM:SS format."""
        if not self.duration:
            return "0:00"
        total_seconds = int(self.duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
