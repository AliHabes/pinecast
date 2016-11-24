from __future__ import absolute_import

import stripe
from django.conf import settings


stripe.api_key = settings.STRIPE_API_KEY
stripe.api_version = '2016-03-07'

__all__ = ['stripe']
