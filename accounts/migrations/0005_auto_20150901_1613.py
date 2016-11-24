# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20150731_0143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='network',
            name='image_url',
            field=models.URLField(null=True, blank=True),
        ),
    ]
