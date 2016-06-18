# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


try:
    import bitfield.models


    class Migration(migrations.Migration):

        dependencies = [
            ('podcasts', '0007_auto_20150901_1613'),
        ]

        operations = [
            migrations.AddField(
                model_name='podcastepisode',
                name='description_flair',
                field=bitfield.models.BitField(((b'feedback_link', 'Feedback Link'), (b'site_link', 'Site Link'), (b'powered_by', 'Powered By Pinecast')), default=0),
            ),
        ]
except ImportError:
    class Migration(migrations.Migration):

        dependencies = [
            ('podcasts', '0007_auto_20150901_1613'),
        ]

        operations = []
