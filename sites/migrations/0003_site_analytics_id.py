# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0002_site_cover_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='analytics_id',
            field=models.CharField(blank=True, max_length=32, null=True, validators=[django.core.validators.RegexValidator(b'^[0-9a-zA-Z\\-]+$', 'Only GA IDs are accepted')]),
        ),
    ]
