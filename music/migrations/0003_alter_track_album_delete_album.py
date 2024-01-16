# Generated by Django 4.2.6 on 2023-11-28 16:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('album', '0001_initial'),
        ('music', '0002_alter_album_artist_alter_track_artist_delete_artist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='track',
            name='album',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='album.album'),
        ),
        migrations.DeleteModel(
            name='Album',
        ),
    ]
