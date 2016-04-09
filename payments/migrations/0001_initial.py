# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-04-03 16:41
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import payments.mixins


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('podcasts', '0011_podcast_total_tips'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringTip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.PositiveIntegerField(default=0, help_text='Value of recurring tip in cents')),
                ('strip_subscription_id', models.CharField(max_length=128)),
                ('deactivated', models.BooleanField(default=False)),
                ('podcast', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='podcast', to='podcasts.Podcast')),
            ],
        ),
        migrations.CreateModel(
            name='TipUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sms_number', models.CharField(blank=True, max_length=32, null=True)),
                ('email_address', models.EmailField(blank=True, max_length=254, null=True)),
                ('created', models.DateTimeField(auto_now=True)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=128, null=True)),
            ],
            bases=(payments.mixins.StripeCustomerMixin, models.Model),
        ),
        migrations.AddField(
            model_name='recurringtip',
            name='tipper',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tipper', to='payments.TipUser'),
        ),
    ]