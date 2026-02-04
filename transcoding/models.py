"""
Models for storing transcoded audio variants.
"""

from django.db import models
from django.conf import settings


class TranscodedTrack(models.Model):
    """
    A transcoded version of an original track at a specific quality level.

    Each original Track may have several TranscodedTrack rows,
    one per quality preset (low / medium / high / lossless).
    """

    QUALITY_CHOICES = [
        ('low', 'Low (96 kbps MP3)'),
        ('medium', 'Medium (160 kbps MP3)'),
        ('high', 'High (320 kbps MP3)'),
        ('lossless', 'Lossless (FLAC)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    original_track = models.ForeignKey(
        'music.Track',
        on_delete=models.CASCADE,
        related_name='transcoded_versions',
    )
    quality = models.CharField(max_length=20, choices=QUALITY_CHOICES)
    codec = models.CharField(
        max_length=20,
        default='mp3',
        help_text='Output codec, e.g. mp3, aac, flac, opus',
    )
    bitrate = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Target bitrate in kbps (null for lossless)',
    )
    sample_rate = models.PositiveIntegerField(
        default=44100,
        help_text='Sample rate in Hz',
    )
    file = models.FileField(upload_to='transcoded/%Y/%m/')
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Size of the transcoded file in bytes',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['original_track', 'quality']
        ordering = ['original_track', 'quality']
        indexes = [
            models.Index(fields=['original_track', 'quality']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.original_track.title} [{self.quality}]"
