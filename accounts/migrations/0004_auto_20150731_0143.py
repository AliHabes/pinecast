# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20150730_2343'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='force_disable_cdn',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usersettings',
            name='force_enable_cdn',
            field=models.BooleanField(default=False),
        ),
    ]
