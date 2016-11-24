# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetimportrequest',
            name='episode',
            field=models.ForeignKey(blank=True, to='podcasts.PodcastEpisode', null=True),
        ),
        migrations.AlterField(
            model_name='assetimportrequest',
            name='failure_message',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='assetimportrequest',
            name='podcast',
            field=models.ForeignKey(blank=True, to='podcasts.Podcast', null=True),
        ),
    ]
