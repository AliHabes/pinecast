from __future__ import absolute_import

import uuid

from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.utils.translation import ugettext

import analytics.analyze as analyze
from accounts.models import UserSettings
from pinecast.helpers import render, reverse, validate_recaptcha


def signup(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    if not req.POST:
        return render(
            req,
            'signup/main.html',
            {'email': req.GET.get('email', '')}
        )

    error = None

    if not _validate_recaptcha(req):
        error = ugettext('Your humanity was not verified')
    elif not req.POST.get('email'):
        error = ugettext('Missing email address')
    elif not req.POST.get('password'):
        error = ugettext('Come on, you need a password')
    elif len(req.POST.get('password')) < 8:
        error = ugettext('Your password needs to be at least 8 characters long')
    elif User.objects.filter(email=req.POST.get('email')).count():
        error = ugettext('That email address is already associated with an account')

    if error:
        return render(req, 'signup/main.html', {
            'error': error,
            'email': req.POST.get('email'),
        })

    try:
        u = User.objects.create_user(
            str(uuid.uuid4())[:30],
            req.POST.get('email'),
            req.POST.get('password')
        )
        u.save()
    except Exception as e:
        return render(req, 'signup/main.html', {
            'error': str(e),
            'email': req.POST.get('email'),
        })

    try:
        us = UserSettings.get_from_user(u)
        us.tz_offset = req.POST.get('timezone')
        us.save()
    except Exception:
        pass  # whatever.

    return redirect(reverse('login') + '?signup_success=true')

def _validate_recaptcha(req):
    response = req.POST.get('g-recaptcha-response')
    ip = analyze.get_request_ip(req)
    return validate_recaptcha(response, ip)
