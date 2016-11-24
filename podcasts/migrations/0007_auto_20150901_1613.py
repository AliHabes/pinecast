# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0006_auto_20150730_2343'),
    ]

    operations = [
        migrations.AlterField(
            model_name='podcastepisode',
            name='copyright',
            field=models.CharField(max_length=1024, blank=True),
        ),
        migrations.AlterField(
            model_name='podcastepisode',
            name='subtitle',
            field=models.CharField(default=b'', max_length=1024, blank=True),
        ),
    ]
