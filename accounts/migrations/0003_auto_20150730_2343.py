# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_network_deactivated'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='plan_podcast_limit_override',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='usersettings',
            name='plan',
            field=models.PositiveIntegerField(default=0, choices=[(0, 'Demo'), (1, 'Starter'), (2, 'Pro'), (3, 'Ultimate'), (4, 'Community')]),
        ),
    ]
