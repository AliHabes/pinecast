from __future__ import absolute_import

import re
import uuid
from urllib.parse import quote as urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.utils.translation import ugettext
from django.views.decorators.http import require_POST

from .models import UserSettings
from .payment_plans import PLAN_COMMUNITY, PLAN_DEMO
from payments.stripe_lib import stripe
from pinecast.email import get_expired_page, get_signed_url, request_must_be_confirmed, send_confirmation_email, send_notification_email
from pinecast.helpers import get_object_or_404, reverse
from pinecast.signatures import signer


def home(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    if settings.DEBUG:
        return redirect('login')

    return redirect('https://www.pinecast.com/')


def login_page(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    ctx = {}
    if req.GET.get('signup_success'):
        ctx['success'] = ugettext('Your account was created successfully. Login below.')
    if req.GET.get('success') == 'resetpassword':
        ctx['success'] = ugettext('Your password was reset successfully.')

    if not req.POST:
        return render(req, 'login.html', ctx)

    try:
        user = User.objects.get(email=req.POST.get('email'))
        password = req.POST.get('password')
    except User.DoesNotExist:
        user = None

    if (user and
        user.is_active and
        user.check_password(password)):
        login(req, authenticate(username=user.username, password=password))
        return redirect('dashboard')

    ctx['error'] = ugettext('Invalid credentials')
    return render(req, 'login.html', ctx)


def forgot_password(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    if not req.POST:
        return render(req, 'forgot_password.html')

    try:
        user = User.objects.get(email=req.POST.get('email'))
    except User.DoesNotExist:
        user = None

    if user and user.is_active:
        send_confirmation_email(
            user,
            ugettext('[Pinecast] Password reset'),
            ugettext('''
We received a request to reset the password for your Pinecast account. If you
do not want to reset your password, please ignore this email.
'''),
            reverse('forgot_password_finalize') + '?email=%s' % urlencode(user.email))
        return render(req, 'forgot_password_success.html')
    return render(req, 'forgot_password.html', {'error': ugettext("We don't recognize that email address.")})


@request_must_be_confirmed
def forgot_password_finalize(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    email = req.GET.get('email')
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return redirect('login')

    ctx = {'email': email,
           'signature': signer.sign(email).decode('utf-8'),
           'error': req.GET.get('error')}

    return render(req, 'forgot_password_finalize.html', ctx)


@require_POST
def forgot_password_finish(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    # Protection against the forces of evil
    sig = req.POST.get('__sig')
    email = req.POST.get('email')
    try:
        h = signer.unsign(sig, max_age=1800).decode('utf-8')
        if h != email:
            raise Exception()
    except Exception:
        return get_expired_page(req)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return redirect('login')

    passwd = req.POST.get('password')
    if passwd != req.POST.get('confirm'):
        err = ugettext("You didn't type the same password twice.")
        return redirect(
            get_signed_url(
                reverse('forgot_password_finalize') +
                '?email=%s&error=%s' % (
                    urlencode(email),
                    urlencode(err))
            )
        )

    user.set_password(passwd)
    user.save()

    return redirect(reverse('login') + '?success=resetpassword')


@login_required
@require_POST
def user_settings_page_savetz(req):
    us = UserSettings.get_from_user(req.user)
    us.tz_offset = float(req.POST.get('timezone'))
    us.save()
    return redirect(reverse('dashboard') + '?success=tz#settings')

@login_required
@require_POST
def user_settings_page_changeemail(req):
    if User.objects.filter(email=req.POST.get('new_email')).count():
        return redirect(reverse('dashboard') + '?error=eae#settings')
    send_confirmation_email(
        req.user,
        ugettext('[Pinecast] Email change confirmation'),
        ugettext('''
Someone requested a change to your email address on Pinecast. This email is
to verify that you own the email address provided.
'''),
        reverse('user_settings_change_email_finalize') + '?user=%s&email=%s' % (
            urlencode(str(req.user.id)), urlencode(req.POST.get('new_email'))),
        req.POST.get('new_email')
    )
    return redirect(reverse('dashboard') + '?success=em#settings')

@login_required
@require_POST
def user_settings_page_changepassword(req):
    if req.POST.get('new_password') != req.POST.get('confirm_password'):
        return redirect(reverse('dashboard') + '?error=pwc#settings')
    if not req.user.check_password(req.POST.get('old_password')):
        return redirect(reverse('dashboard') + '?error=pwo#settings')
    if len(req.POST.get('new_password')) < 8:
        return redirect(reverse('dashboard') + '?error=pwl#settings')

    req.user.set_password(req.POST.get('new_password'))
    req.user.save()

    send_notification_email(
        req.user,
        ugettext('[Pinecast] Password changed'),
        ugettext('''
Your Pinecast password has been updated. If you did not request this change,
please contact Pinecast support as soon as possible at
support@pinecast.zendesk.com.
''')
    )
    return redirect(reverse('login'))

@login_required
@request_must_be_confirmed
def user_settings_page_changeemail_finalize(req):
    user = get_object_or_404(User, id=req.GET.get('user'))
    user.email = req.GET.get('email')
    user.save()
    return redirect(reverse('dashboard') + '?success=emf#settings')


@login_required
@require_POST
def new_referral_code(req):
    us = UserSettings.get_from_user(req.user)
    if us.plan == PLAN_DEMO or us.plan == PLAN_COMMUNITY:
        return redirect('dashboard')

    # Ignore users that already have codes
    if us.coupon_code:
        return redirect('dashboard')

    code = 'r-' + str(uuid.uuid4())[-6:]
    coupon = stripe.Coupon.create(
        id=code,
        percent_off=settings.REFERRAL_DISCOUNT,
        duration='repeating',
        duration_in_months=settings.REFERRAL_DISCOUNT_DURATION,
        metadata={'owner_id': req.user.id})

    us.coupon_code = code
    us.save()

    return redirect(reverse('dashboard') + '#referrals')
