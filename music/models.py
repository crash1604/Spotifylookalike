from django.db import models


def upload_location(instance, filename):
    return '{0}/{1}/{2}'.format(instance.artist, instance.album, filename)


class AudioTrack(models.Model):
    title = models.TextField()
    credits = models.TextField(null=True, blank=True)
    artist = models.CharField(null=False, blank=False, max_length=255, default='your name', unique=False)
    album = models.CharField(max_length=255, default='Single', unique=False)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    document = models.FileField(upload_to=upload_location)
