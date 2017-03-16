# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-16 16:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0030_auto_20170312_2333'),
    ]

    operations = [
        migrations.AlterField(
            model_name='podcast',
            name='private_access_min_subscription',
            field=models.PositiveIntegerField(blank=True, default=None, help_text='Min sub value in cents', null=True),
        ),
        migrations.AlterField(
            model_name='podcast',
            name='private_after_age',
            field=models.PositiveIntegerField(blank=True, default=None, help_text='Age in seconds', null=True),
        ),
        migrations.AlterField(
            model_name='podcast',
            name='private_after_nth',
            field=models.PositiveIntegerField(blank=True, default=None, null=True),
        ),
    ]
