# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-04-25 03:16
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0012_auto_20160414_0301'),
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('occurred_at', models.DateTimeField(auto_now=True)),
                ('amount', models.PositiveIntegerField(default=0, help_text='Value of tip in cents')),
                ('fee_amount', models.PositiveIntegerField(default=0, help_text='Value of application fee in cents')),
                ('podcast', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tip_events', to='podcasts.Podcast')),
                ('tipper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tip_events', to='payments.TipUser')),
            ],
        ),
        migrations.AlterField(
            model_name='recurringtip',
            name='podcast',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_tips', to='podcasts.Podcast'),
        ),
        migrations.AlterField(
            model_name='recurringtip',
            name='tipper',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_tips', to='payments.TipUser'),
        ),
    ]