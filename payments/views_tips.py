from urllib import quote

import rollbar
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext
from django.views.decorators.http import require_POST

from .models import TipEvent, TipUser
from .stripe_lib import stripe
from accounts.payment_plans import PLAN_DEMO, PLAN_TIP_LIMITS
from accounts.models import UserSettings
from dashboard.views import _pmrender
from pinecast.email import (send_anon_confirmation_email as send_email,
                            send_notification_email,
                            validate_confirmation)
from pinecast.helpers import json_response, reverse
from podcasts.models import Podcast


def no_session(req, ctx):
    if not req.POST:
        return _pmrender(req, 'payments/tip_jar/login.html', ctx)

    has_user = False
    if req.POST.get('email'):
        email = req.POST.get('email')
        tip_user = None
        try:
            tip_user = TipUser.objects.get(email_address=email)
            has_user = True
        except TipUser.DoesNotExist:
            try:
                tip_user = TipUser(email_address=email)
                tip_user.save()
                has_user = True
            except Exception as e:
                pass

        if has_user:
            send_email(
                email,
                ugettext('Leave a tip for %s') % ctx['podcast'].name,
                ugettext(
                    'Thanks for verifying your email! Click the link below '
                    'to choose your level of support for %s.' %
                        ctx['podcast'].name),
                reverse('tip_jar', podcast_slug=ctx['podcast'].slug) +
                    '?email=%s' % quote(email))

    if has_user:
        return _pmrender(req, 'payments/tip_jar/check_email.html', ctx)

    ctx['error'] = ugettext('That email address did not work.')
    return _pmrender(req, 'payments/tip_jar/login.html', ctx)


def create_session(req, ctx):
    validates = validate_confirmation(req)
    email = req.GET.get('email')
    if not validates or not email:
        return redirect(
            reverse('tip_jar', podcast_slug=ctx['podcast'].slug) +
            '?error=bad_token')

    # This should never throw, unless the TipUser was manually deleted.
    # The validated URL should never have been created if a TipUser was not
    # saved for that email.
    tip_user = TipUser.objects.get(email_address=email)

    req.session['pay_session'] = tip_user.id
    return tip_flow(req, ctx, tip_user)


def tip_flow(req, ctx, tip_user=None):
    # Same logic here as above.
    tip_user = tip_user or TipUser.objects.get(id=req.session['pay_session'])

    ctx['tipper'] = tip_user
    ctx['existing_card'] = tip_user.get_card_info()

    return _pmrender(req, 'payments/tip_jar/main.html', ctx)


@require_POST
@json_response
def set_tip_payment_method(req):
    if not req.session.get('pay_session'):
        return {'error': 'no session'}

    tip_user = get_object_or_404(TipUser, id=req.session['pay_session'])
    customer = tip_user.get_stripe_customer()
    if customer:
        customer.source = req.POST.get('token')
        customer.save()
    else:
        tip_user.create_stripe_customer(req.POST.get('token'))

    return {'success': True, 'id': tip_user.stripe_customer_id}


@require_POST
@json_response
def send_tip(req):
    if not req.session.get('pay_session'):
        return {'error': 'no session'}

    try:
        amount = int(req.POST.get('amount'))
        if amount < 100:
            return {'error': ugettext('Tips less than $1 are not allowed.')}
    except Exception:
        return {'error': 'bad amount'}


    pod = get_object_or_404(Podcast, slug=req.POST.get('podcast'))
    owner_us = UserSettings.get_from_user(pod.owner)
    if amount > PLAN_TIP_LIMITS[owner_us.plan]:
        return {'error': ugettext('That tip is too large for %s') % pod.name}


    tip_user = get_object_or_404(TipUser, id=req.session['pay_session'])
    customer = tip_user.get_stripe_customer()
    if not customer:
        return {'error': 'no customer'}

    application_fee = int(amount * 0.05) if owner_us.plan == PLAN_DEMO else 0

    try:
        stripe.Charge.create(
            amount=amount,
            application_fee=application_fee,
            currency='usd',
            customer=customer.id,
            description='Tip for %s' % pod.name,
            destination=owner_us.stripe_payout_managed_account,
        )

    except Exception as e:
        rollbar.report_message('Error when sending tip: %s' % str(e), 'error')
        return {'error': str(e)}

    else:
        pod.total_tips += amount
        pod.tip_value += amount - application_fee
        pod.save()

        tip_event = TipEvent(
            tipper=tip_user,
            podcast=pod,
            amount=amount,
            fee_amount=application_fee)
        tip_event.save()

    send_notification_email(
        None,
        'Thanks for leaving a tip!',
        'Your tip was processed: %s received $%d. Thanks for supporting your '
            'favorite content creators!' % (
                pod.name, float(amount) / 100),
        email=tip_user.email_address)
    send_notification_email(
        pod.owner,
        'Your podcast was tipped!',
        '%s received was tipped $%d by %s. You should send them an email '
            'thanking them for their generosity.' % (
                pod.name, float(amount) / 100, tip_user.email_address))

    return {'success': True}
