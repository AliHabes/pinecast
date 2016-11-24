from __future__ import absolute_import
from __future__ import print_function

import hashlib
import uuid

import itsdangerous
import rollbar
from boto3.session import Session
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.utils.translation import ugettext

from .signatures import signer


CONFIRMATION_PARAM = '__ctx'


def _send_mail(to, subject, body, email_format='Text'):
    if settings.DEBUG:
        print((to, subject, body))
    session = Session(aws_access_key_id=settings.SES_ACCESS_ID,
                      aws_secret_access_key=settings.SES_SECRET_KEY,
                      region_name='us-east-1')
    conn = session.client('ses')
    resp = conn.send_email(
        Source=settings.SENDER_EMAIL,
        Destination={'ToAddresses': [to]},
        Message={
            'Subject': {
                'Data': subject,
            },
            'Body': {
                email_format: {
                    'Data': body,
                },
            },
        },
        ReplyToAddresses=[settings.SUPPORT_EMAIL],
        ReturnPath=settings.ADMINS[0][1]
    )
    if not resp.get('MessageId'):
        rollbar.report_message('Got bad response from SES: %s' % repr(resp), 'error')


def send_confirmation_email(user, subject, description, url, email=None):
    email = email or user.email
    signed_url = get_signed_url(url)
    body = ugettext('''{description}

To confirm this request, visit the link below.

https://pinecast.com{url}
''').format(description=description, url=signed_url)
    return send_notification_email(user, subject, body, email)


def send_notification_email(user, subject, description, email=None):
    email = email or user.email
    body = ugettext('''{greeting}

{description}

Thanks,
The Pinecast Team
    ''').format(
        description=description,
        greeting='Hey Pinecaster,' if user else 'Hi there,')
    return _send_mail(email, subject, body)


def send_anon_confirmation_email(to, subject, body, url):
    signed_url = get_signed_url(url)
    constructed_body = ugettext('''{body}

https://pinecast.com{url}
''').format(body=body, url=signed_url)
    return _send_mail(to, subject, constructed_body)


def validate_confirmation(req, max_age=settings.EMAIL_CONFIRMATION_MAX_AGE):
    full_path = req.get_full_path()
    if CONFIRMATION_PARAM not in full_path:
        return False
    param_loc = full_path.index(CONFIRMATION_PARAM)
    trimmed_path = full_path[:param_loc - 1]
    signed = req.GET.get(CONFIRMATION_PARAM)
    try:
        signature = signer.unsign(signed, max_age=max_age)
        return hashlib.sha1(trimmed_path).hexdigest() == signature
    except itsdangerous.BadTimeSignature:
        return False


def request_must_be_confirmed(view):
    def wrap(*args, **kwargs):
        if not validate_confirmation(args[0]):
            return get_expired_page(args[0])
        return view(*args, **kwargs)
    return wrap


def get_signed_url(url):
    if not url.startswith('/'):
        url = '/%s' % url
    if '?' in url:
        signed_url = '%s&' % url
    else:
        signed_url = '%s?' % url

    token = hashlib.sha1(url).hexdigest()
    signed_url += '%s=%s' % (CONFIRMATION_PARAM, signer.sign(token))
    return signed_url


def get_expired_page(req):
    return HttpResponseBadRequest(render(req, 'bad_signature.html'))
