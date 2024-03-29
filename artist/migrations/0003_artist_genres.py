# Generated by Django 4.2.6 on 2023-11-28 16:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0001_initial'),
        ('artist', '0002_remove_artist_genres'),
    ]

    operations = [
        migrations.AddField(
            model_name='artist',
            name='genres',
            field=models.ManyToManyField(blank=True, related_name='artists', to='music.genre'),
        ),
    ]
