from django.db import models


# Create your models here.

class Track(models.Model):
    title = models.TextField()
    credits = models.TextField(null=True, blank=True)
