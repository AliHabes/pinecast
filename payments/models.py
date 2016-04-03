from django.db import models
from django.utils.translation import ugettext_lazy

from payments.mixins import StripeCustomerMixin
from podcasts.models import Podcast


class TipUser(StripeCustomerMixin, models.Model):
    sms_number = models.CharField(max_length=32, blank=True, null=True)
    email_address = models.EmailField(blank=True, null=True)

    created = models.DateTimeField(auto_now=True)

    stripe_customer_id = models.CharField(max_length=128, blank=True, null=True)


class RecurringTip(models.Model):
    tipper = models.ForeignKey(TipUser, related_name='tipper')
    podcast = models.ForeignKey(Podcast, related_name='podcast')

    amount = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy('Value of recurring tip in cents'))

    strip_subscription_id = models.CharField(max_length=128)

    deactivated = models.BooleanField(default=False)
