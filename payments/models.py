import datetime
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy

from .stripe_lib import stripe
from accounts.models import UserSettings
from payments.mixins import StripeCustomerMixin
from podcasts.models import Podcast


class TipUser(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    email_address = models.EmailField(blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    @classmethod
    def tip_user_from(cls, auto_save=True, **kwargs):
        try:
            return cls.objects.get(**kwargs)
        except cls.DoesNotExist:
            x = cls(**kwargs)
            if auto_save: x.save()
            return x

    def get_email(self):
        return self.email_address

    def __str__(self):
        return '%s%s' % (self.email_address, ' (v)' if self.verified else '')


class RecurringTip(models.Model):
    tipper = models.ForeignKey(TipUser, related_name='recurring_tips')
    podcast = models.ForeignKey(Podcast, related_name='recurring_tips')

    created = models.DateTimeField(auto_now_add=True)

    amount = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy('Value of recurring tip in cents'))

    stripe_customer_id = models.CharField(max_length=128)
    stripe_subscription_id = models.CharField(max_length=128)

    deactivated = models.BooleanField(default=False)

    def __str__(self):
        return '%s - %s' % (self.tipper.email_address, self.amount)

    def get_subscription(self):
        us = UserSettings.get_from_user(self.podcast.owner)
        stripe_account = us.stripe_payout_managed_account
        try:
            return stripe.Subscription.retrieve(
                self.stripe_subscription_id, stripe_account=stripe_account)
        except stripe.error.InvalidRequestError:
            return None

    def cancel(self):
        us = UserSettings.get_from_user(self.podcast.owner)
        try:
            subscription = stripe.Subscription.retrieve(
                self.stripe_subscription_id,
                stripe_account=us.stripe_payout_managed_account)
        except stripe.error.InvalidRequestError:
            pass
        else:
            subscription.delete()
        finally:
            self.deactivated = True
            self.save()


class TipEvent(models.Model):
    tipper = models.ForeignKey(TipUser, related_name='tip_events', null=True)
    podcast = models.ForeignKey(Podcast, related_name='tip_events')
    occurred_at = models.DateTimeField(auto_now_add=True)

    stripe_charge = models.CharField(max_length=64, null=True)
    recurring_tip = models.ForeignKey(RecurringTip, related_name='tip_events', null=True)

    amount = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy('Value of tip in cents'))
    fee_amount = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy('Value of application fee in cents'))

    def payout_date(self):
        date = self.occurred_at.date()

        # This payout date is the last one that the last tip missed the cutoff
        # for.
        following_payout = date + datetime.timedelta(days=(5 - date.isoweekday()) % 7)

        return following_payout + datetime.timedelta(days=7)
