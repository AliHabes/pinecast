# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0004_auto_20150723_1539'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetImportRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now=True)),
                ('expiration', models.DateTimeField()),
                ('audio_source_url', models.URLField(blank=True)),
                ('image_source_url', models.URLField(blank=True)),
                ('access_token', models.CharField(max_length=128)),
                ('resolved', models.BooleanField(default=False)),
                ('failed', models.BooleanField(default=False)),
                ('failure_message', models.TextField(null=True)),
                ('episode', models.ForeignKey(to='podcasts.PodcastEpisode', null=True)),
                ('podcast', models.ForeignKey(to='podcasts.Podcast', null=True)),
            ],
        ),
    ]
