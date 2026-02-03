"""
Models for streaming-related data.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PlayHistory(models.Model):
    """
    Tracks user listening history.
    Used for recommendations, recently played, and analytics.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='play_history'
    )
    track = models.ForeignKey(
        'music.Track',
        on_delete=models.CASCADE,
        related_name='play_records'
    )
    played_at = models.DateTimeField(default=timezone.now, db_index=True)
    duration_listened = models.DurationField(
        null=True,
        blank=True,
        help_text='How long the user listened to this track'
    )
    completed = models.BooleanField(
        default=False,
        help_text='Whether the user listened to the entire track'
    )
    context = models.CharField(
        max_length=50,
        blank=True,
        help_text='Context of play: playlist, album, search, radio, etc.'
    )
    context_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='ID of the context (playlist_id, album_id, etc.)'
    )

    class Meta:
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['user', '-played_at']),
            models.Index(fields=['track', '-played_at']),
        ]

    def __str__(self):
        return f"{self.user.username} played {self.track.title} at {self.played_at}"


class StreamSession(models.Model):
    """
    Tracks active streaming sessions.
    Useful for limiting concurrent streams and analytics.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='stream_sessions'
    )
    track = models.ForeignKey(
        'music.Track',
        on_delete=models.CASCADE,
        related_name='stream_sessions'
    )
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)
    quality = models.CharField(max_length=20, default='medium')
    device_type = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        return f"Session {self.session_id} - {self.user.username}"


class UserFavorite(models.Model):
    """
    User's favorited/liked tracks.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    track = models.ForeignKey(
        'music.Track',
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'track']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} favorited {self.track.title}"


class UserQueue(models.Model):
    """
    User's playback queue.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='queue'
    )
    current_track = models.ForeignKey(
        'music.Track',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='currently_playing'
    )
    current_position = models.PositiveIntegerField(
        default=0,
        help_text='Current position in queue'
    )
    shuffle = models.BooleanField(default=False)
    repeat_mode = models.CharField(
        max_length=10,
        choices=[
            ('off', 'Off'),
            ('all', 'Repeat All'),
            ('one', 'Repeat One'),
        ],
        default='off'
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Queue for {self.user.username}"


class QueueTrack(models.Model):
    """
    Individual track in a user's queue.
    """
    queue = models.ForeignKey(
        UserQueue,
        on_delete=models.CASCADE,
        related_name='tracks'
    )
    track = models.ForeignKey(
        'music.Track',
        on_delete=models.CASCADE
    )
    position = models.PositiveIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position']
        unique_together = ['queue', 'position']

    def __str__(self):
        return f"{self.track.title} at position {self.position}"
