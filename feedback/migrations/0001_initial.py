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
            name='Feedback',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now=True)),
                ('sender', models.EmailField(max_length=254)),
                ('message', models.TextField()),
                ('episode', models.ForeignKey(blank=True, to='podcasts.PodcastEpisode', null=True)),
                ('podcast', models.ForeignKey(to='podcasts.Podcast')),
            ],
        ),
    ]
