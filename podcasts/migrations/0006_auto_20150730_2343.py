# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0005_podcastreviewassociation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='podcast',
            name='rss_redirect',
            field=models.URLField(null=True, blank=True),
        ),
    ]
