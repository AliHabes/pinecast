# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0003_site_analytics_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='cover_image_url',
            field=models.URLField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='itunes_url',
            field=models.URLField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='logo_url',
            field=models.URLField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='stitcher_url',
            field=models.URLField(null=True, blank=True),
        ),
    ]
