import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy

import payment_plans
from pinecast.helpers import cached_method
from payments.mixins import StripeCustomerMixin


class UserSettings(StripeCustomerMixin, models.Model):
    user = models.OneToOneField(User)
    plan = models.PositiveIntegerField(default=0, choices=payment_plans.PLANS)
    tz_offset = models.SmallIntegerField(default=0)  # Default to UTC

    plan_podcast_limit_override = models.PositiveIntegerField(default=0)  # Podcast limit = max(pplo, plan.max)

    stripe_customer_id = models.CharField(max_length=128, blank=True, null=True)
    stripe_payout_managed_account = models.CharField(max_length=128, blank=True, null=True)

    def clean(self):
        if self.tz_offset < -12 or self.tz_offset > 14:
            raise ValidationError('Timezone offset must be between -12 and 14, inclusive')

    @classmethod
    def get_from_user(cls, user):
        try:
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            us = UserSettings(user=user)
            us.save()
            return us

    @classmethod
    def user_meets_plan(cls, user, min_plan):
        uset = cls.get_from_user(user)
        return payment_plans.minimum(uset.plan, min_plan)

    @cached_method
    def get_tz_delta(self):
        return datetime.timedelta(hours=self.tz_offset)

    def get_email(self):
        return self.user.email

    def get_stripe_description(self):
        return 'user:%d' % self.user.id


class Network(models.Model):
    owner = models.ForeignKey(User, related_name='network_ownership')
    name = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now=True)

    image_url = models.URLField(blank=True, null=True, max_length=500)
    deactivated = models.BooleanField(default=False)

    members = models.ManyToManyField(User)

    def __unicode__(self):
        return self.name

    @cached_method
    def get_member_count(self):
        return self.members.count()

    @cached_method
    def get_podcast_count(self):
        return self.podcast_set.count()
