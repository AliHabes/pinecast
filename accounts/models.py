from __future__ import absolute_import

import datetime
import sys

import rollbar
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy

from . import payment_plans
from pinecast.email import send_notification_email
from pinecast.helpers import cached_method
from payments.mixins import StripeCustomerMixin, StripeManagedAccountMixin
from payments.stripe_lib import stripe


class UserSettings(StripeCustomerMixin, StripeManagedAccountMixin, models.Model):
    user = models.OneToOneField(User)
    plan = models.PositiveIntegerField(default=0, choices=payment_plans.PLANS)
    tz_offset = models.SmallIntegerField(default=0)  # Default to UTC

    plan_podcast_limit_override = models.PositiveIntegerField(default=0)  # Podcast limit = max(pplo, plan.max)

    stripe_customer_id = models.CharField(max_length=128, blank=True, null=True)
    stripe_payout_managed_account = models.CharField(max_length=128, blank=True, null=True)

    coupon_code = models.CharField(max_length=16, blank=True, null=True)

    def clean(self):
        if self.tz_offset < -12 or self.tz_offset > 14:
            raise ValidationError('Timezone offset must be between -12 and 14, inclusive')

    @classmethod
    def get_from_user(cls, user):
        try:
            return user.usersettings
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

    def set_plan(self, new_plan_val, coupon=None):
        orig_plan = self.plan
        user = self.user
        customer = self.get_stripe_customer()
        if not customer:
            return False

        was_upgrade = (
            payment_plans.PLAN_RANKS[orig_plan] <= payment_plans.PLAN_RANKS[new_plan_val])

        # Handle pro downgrades
        if orig_plan == payment_plans.PLAN_PRO and not was_upgrade:
            # Remove collaborators
            from dashboard.models import Collaborator
            Collaborator.objects.filter(podcast__in=user.podcast_set.all()).delete()

            # Remove private threshold on episodes
            self.user.podcast_set.update(private_access_min_subscription=None)

        existing_subs = customer.subscriptions.all(limit=1)['data']

        # Handle downgrades to free
        if new_plan_val == payment_plans.PLAN_DEMO:
            if existing_subs:
                existing_sub = existing_subs[0]
                existing_sub.delete()

            for podcast in self.user.podcast_set.all():
                for tip in podcast.recurring_tips.all():
                    tip.cancel()

            self.plan = payment_plans.PLAN_DEMO
            if self.coupon_code:
                stripe.Coupon.retrieve(self.coupon_code).delete()
                self.coupon_code = None
            self.save()
            return True

        plan_stripe_id = payment_plans.STRIPE_PLANS[new_plan_val]

        if existing_subs:
            existing_sub = existing_subs[0]
            existing_sub.plan = plan_stripe_id

            if was_upgrade and coupon:
                existing_sub.coupon = coupon

            try:
                existing_sub.save()
            except Exception as e:
                rollbar.report_exc_info(sys.exc_info())
                return 'card_error'
        else:
            try:
                customer.subscriptions.create(
                    coupon=coupon,
                    plan=plan_stripe_id)
            except stripe.error.CardError:
                return 'card_error'
            except Exception as e:
                rollbar.report_exc_info(sys.exc_info())
                return 'card_error'

        self.plan = new_plan_val
        self.save()

        send_notification_email(
            user,
            ugettext('Your account has been %s') %
                (ugettext('upgraded') if was_upgrade else ugettext('downgraded')),
            ugettext('Your Pinecast account has been updated successfully. '
                     'Your account is now marked as "%s".\n\n'
                     'Please contact Pinecast support if you have any '
                     'questions.') %
                payment_plans.PLANS_MAP[new_plan_val])
        return True


class Network(models.Model):
    owner = models.ForeignKey(User, related_name='network_ownership')
    name = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now_add=True)

    image_url = models.URLField(blank=True, null=True, max_length=500)
    deactivated = models.BooleanField(default=False)

    members = models.ManyToManyField(User)

    def __str__(self):
        return self.name

    @cached_method
    def get_member_count(self):
        return self.members.count()

    @cached_method
    def get_podcast_count(self):
        return self.podcast_set.count()
