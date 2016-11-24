from __future__ import absolute_import

import itsdangerous
from django.conf import settings

signer = itsdangerous.TimestampSigner(settings.SECRET_KEY)
