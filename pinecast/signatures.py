from __future__ import absolute_import

import itsdangerous
from django.conf import settings

signer_nots = itsdangerous.Signer(settings.SECRET_KEY)
signer = itsdangerous.TimestampSigner(settings.SECRET_KEY)
