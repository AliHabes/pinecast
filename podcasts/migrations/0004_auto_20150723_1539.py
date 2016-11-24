# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0003_auto_20150718_1753'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='episodeimportrequest',
            name='episode',
        ),
        migrations.AlterField(
            model_name='podcast',
            name='copyright',
            field=models.CharField(max_length=1024, blank=True),
        ),
        migrations.DeleteModel(
            name='EpisodeImportRequest',
        ),
    ]
