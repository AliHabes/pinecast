# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Podcast',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('slug', models.SlugField(unique=True)),
                ('name', models.CharField(max_length=256)),
                ('subtitle', models.CharField(default=b'', max_length=512)),
                ('created', models.DateTimeField(auto_now=True)),
                ('cover_image', models.URLField()),
                ('description', models.TextField()),
                ('is_explicit', models.BooleanField()),
                ('homepage', models.URLField()),
                ('language', models.CharField(max_length=16)),
                ('copyright', models.CharField(max_length=1024)),
                ('author_name', models.CharField(max_length=1024)),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PodcastEpisode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('title', models.CharField(max_length=1024)),
                ('subtitle', models.CharField(default=b'', max_length=1024)),
                ('created', models.DateTimeField(auto_now=True)),
                ('publish', models.DateTimeField()),
                ('description', models.TextField()),
                ('duration', models.PositiveIntegerField(help_text=b'Audio duration in seconds')),
                ('audio_url', models.URLField()),
                ('audio_size', models.PositiveIntegerField(default=0)),
                ('audio_type', models.CharField(max_length=64)),
                ('image_url', models.URLField()),
                ('copyright', models.CharField(max_length=1024)),
                ('license', models.CharField(max_length=1024)),
                ('podcast', models.ForeignKey(to='podcasts.Podcast')),
            ],
        ),
    ]
