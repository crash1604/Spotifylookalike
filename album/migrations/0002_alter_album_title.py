# Generated by Django 4.2.6 on 2024-02-18 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('album', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='album',
            name='title',
            field=models.CharField(max_length=200, unique=True),
        ),
    ]
