import datetime

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy

from payments.mixins import StripeCustomerMixin
from podcasts.models import Podcast


class TipUser(StripeCustomerMixin, models.Model):
    sms_number = models.CharField(max_length=32, blank=True, null=True)
    email_address = models.EmailField(blank=True, null=True)

    created = models.DateTimeField(auto_now=True)

    stripe_customer_id = models.CharField(max_length=128, blank=True, null=True)

    def get_email(self):
        return self.email_address


class TipEvent(models.Model):
    tipper = models.ForeignKey(TipUser, related_name='tip_events')
    podcast = models.ForeignKey(Podcast, related_name='tip_events')
    occurred_at = models.DateTimeField(auto_now=True)
    if settings.DEBUG:
        occurred_at.editable = True

    stripe_charge = models.CharField(max_length=64, null=True)

    amount = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy('Value of tip in cents'))
    fee_amount = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy('Value of application fee in cents'))

    def payout_date(self):
        date = self.occurred_at.date()
        print date

        # This payout date is the last one that the last tip missed the cutoff
        # for.
        following_payout = date + datetime.timedelta(days=(5 - date.isoweekday()) % 7)
        print following_payout

        return following_payout + datetime.timedelta(days=7)



class RecurringTip(models.Model):
    tipper = models.ForeignKey(TipUser, related_name='recurring_tips')
    podcast = models.ForeignKey(Podcast, related_name='recurring_tips')

    amount = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy('Value of recurring tip in cents'))

    strip_subscription_id = models.CharField(max_length=128)

    deactivated = models.BooleanField(default=False)
