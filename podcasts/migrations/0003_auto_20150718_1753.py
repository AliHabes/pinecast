# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('podcasts', '0002_auto_20150706_0311'),
    ]

    operations = [
        migrations.CreateModel(
            name='EpisodeImportRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('expiration', models.DateTimeField()),
                ('audio_source_url', models.URLField()),
                ('image_source_url', models.URLField(blank=True)),
                ('access_token', models.CharField(max_length=128)),
            ],
        ),
        migrations.AddField(
            model_name='podcast',
            name='networks',
            field=models.ManyToManyField(to='accounts.Network'),
        ),
        migrations.AddField(
            model_name='podcastepisode',
            name='awaiting_import',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='podcastepisode',
            name='license',
            field=models.CharField(max_length=1024, blank=True),
        ),
        migrations.AddField(
            model_name='episodeimportrequest',
            name='episode',
            field=models.ForeignKey(to='podcasts.PodcastEpisode'),
        ),
    ]
