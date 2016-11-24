# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0008_podcastepisode_description_flair'),
        ('feedback', '0002_feedback_sender_ip'),
    ]

    operations = [
        migrations.CreateModel(
            name='EpisodeFeedbackPrompt',
            fields=[
                ('episode', models.OneToOneField(primary_key=True, serialize=False, to='podcasts.PodcastEpisode')),
                ('prompt', models.TextField()),
            ],
        ),
    ]
