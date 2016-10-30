import json

import iso8601
import rollbar
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import accounts.payment_plans as payment_plans
import views_tips
from .models import RecurringTip, TipEvent
from .stripe_lib import stripe
from accounts.models import UserSettings
from dashboard.views import _pmrender
from pinecast.email import CONFIRMATION_PARAM, send_notification_email
from pinecast.helpers import get_object_or_404, json_response, reverse
from podcasts.models import Podcast


BASE_URL = 'https://pinecast.com' if not settings.DEBUG else 'http://localhost:8000'


@login_required
def upgrade(req):
    us = UserSettings.get_from_user(req.user)
    customer = us.get_stripe_customer()

    ctx = {
        'error': req.GET.get('error'),
        'stripe_customer': customer,
    }
    return _pmrender(req, 'payments/main.html', ctx)


AVAILABLE_PLANS = {
    'demo': payment_plans.PLAN_DEMO,
    'starter': payment_plans.PLAN_STARTER,
    'pro': payment_plans.PLAN_PRO,
}

@require_POST
@login_required
def upgrade_set_plan(req):
    new_plan = req.POST.get('plan')
    if new_plan not in AVAILABLE_PLANS:
        return redirect('upgrade')

    new_plan_val = AVAILABLE_PLANS[new_plan]

    us = UserSettings.get_from_user(req.user)
    result = us.set_plan(new_plan_val)

    if not result:
        return redirect('upgrade')
    elif result == 'card_error':
        return redirect(reverse('upgrade') + '?error=card')
    else:
        return redirect(reverse('upgrade') + '?success')


@require_POST
@login_required
def set_payment_method_redir(req):
    us = UserSettings.get_from_user(req.user)
    customer = us.get_stripe_customer()

    if req.POST.get('next_url') == 'upgrade':
        next_url = reverse('upgrade')
    else:
        next_url = reverse('dashboard')

    try:
        if customer:
            customer.source = req.POST.get('token')
            customer.save()
        else:
            us.create_stripe_customer(req.POST.get('token'))
    except stripe.error.CardError as e:
        return redirect(next_url + '?error=crej#settings')
    except Exception as e:
        rollbar.report_message(str(e), 'error')
        return redirect(next_url + '?error=cerr#settings')

    return redirect(next_url + '?success=csuc#settings')


@require_POST
@login_required
@json_response
def set_tip_cashout(req):
    try:
        dob = iso8601.parse_date(req.POST.get('dob'))
    except Exception:
        return {'success': False, 'error': 'invalid dob'}

    forwarded_for = req.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        ip = forwarded_for.split(',')[0]
    else:
        ip = req.META.get('REMOTE_ADDR')

    legal_entity = {
        'address': {
            'city': req.POST.get('addressCity'),
            'state': req.POST.get('addressState'),
            'postal_code': req.POST.get('addressZip'),
            'line1': req.POST.get('addressStreet'),
            'line2': req.POST.get('addressSecond'),
        },
        'ssn_last_4': req.POST.get('ssnLastFour'),
        'dob': {
            'day': dob.day,
            'month': dob.month,
            'year': dob.year,
        },
        'first_name': req.POST.get('firstName'),
        'last_name': req.POST.get('lastName'),
        'type': 'individual',
    }

    us = UserSettings.get_from_user(req.user)
    account = us.get_stripe_managed_account()
    if account:
        account.external_account = req.POST.get('token')
        for key in legal_entity:
            setattr(account.legal_entity, key, legal_entity[key])
        account.save()
    else:
        us.create_stripe_managed_account(
            req.POST.get('token'), ip, legal_entity)

    return {'success': True}


@csrf_exempt
@require_POST
def hook(req):
    try:
        body = json.loads(req.body)
    except Exception as e:
        rollbar.report_message(
            'Error parsing Stripe hook JSON: %s' % str(e), 'warn')
        return HttpResponse(status=400)

    if not settings.DEBUG:
        try:
            # Validate the event
            stripe.Event.retrieve(
                body['id'], stripe_account=body.get('user_id'))
        except Exception as e:
            rollbar.report_message(
                'Error fetching Stripe event: %s' % str(e), 'warn')
            return HttpResponse(status=400)


    if body['type'] == 'invoice.payment_succeeded' and body.get('user_id'):
        sub = _get_subscription(body)
        if not sub: return HttpResponse(status=200)

        amount = int(body['data']['object']['total'])
        pod = sub.podcast

        tip_event = TipEvent(
            tipper=sub.tipper,
            podcast=pod,
            amount=amount,
            recurring_tip=sub)
        tip_event.save()

        pod.total_tips += amount
        pod.save()

        email = sub.tipper.email_address
        send_notification_email(
            None,
            ugettext('Thanks for leaving a tip!'),
            ugettext('Your tip was sent: %s received $%0.2f. Thanks for supporting your '
                     'favorite content creators!') % (pod.name, float(amount) / 100),
            email=email)
        send_notification_email(
            pod.owner,
            ugettext('%s received a tip of $%0.2f') % (pod.name, float(amount) / 100),
            ugettext('%s received a tip of $%0.2f from %s as part of a monthly '
                     'subscription to the show. You should send them an email '
                     'thanking them for their generosity.') %
                (pod.name, float(amount) / 100, email))

    elif body['type'] == 'invoice.payment_failed':
        if body.get('user_id'):
            _handle_failed_tip_sub(body)
        else:
            _handle_failed_subscription(body)

    return HttpResponse(status=200)


def _get_subscription(event_body):
    sub_id = event_body['data']['object']['subscription']
    try:
        return RecurringTip.objects.get(stripe_subscription_id=sub_id)
    except RecurringTip.DoesNotExist:
        rollbar.report_message(
            'Event on unknown subscription: %s' % sub_id, 'warn')
        return None


def _handle_failed_tip_sub(body):
    sub = _get_subscription(body)
    if not sub: return HttpResponse(status=200)

    closed = body['data']['object']['closed']
    pod = sub.podcast
    if closed:
        sub.deactivated = True
        sub.save()

        send_notification_email(
            None,
            ugettext('Your subscription to %s was cancelled') % pod.name,
            ugettext('We attempted to charge your card for your '
                     'subscription to %s, but the payment failed multiple '
                     'times. If you wish to remain subscribed, please '
                     'visit the link below to enter new payment '
                     'information.\n\n%s') %
                (pod.name, BASE_URL + reverse('tip_jar', podcast_slug=pod.slug)),
            email=sub.tipper.email_address)
    else:
        send_notification_email(
            None,
            ugettext('Your subscription to %s has problems') % pod.name,
            ugettext('We attempted to charge your card for your '
                     'subscription to %s, but the payment failed. Please '
                     'visit the tip jar and update your subscription with '
                     'new card details as soon as possible. You can do that '
                     'at the link below.\n\n%s') %
                (pod.name, BASE_URL + reverse('tip_jar', podcast_slug=pod.slug)),
            email=sub.tipper.email_address)


def _handle_failed_subscription(body):
    customer = body['data']['object']['customer']
    try:
        us = UserSettings.objects.get(stripe_customer_id=customer)
    except UserSettings.DoesNotExist:
        rollbar.report_message('Unknown customer: %s' % customer, 'warn')
        return

    closed = body['data']['object']['closed']
    user = us.user
    if closed:
        us.set_plan(payment_plans.PLAN_DEMO)
        send_notification_email(
            user,
            ugettext('Your Pinecast subscription was cancelled.'),
            ugettext('Pinecast attempted to charge your payment card multiple '
                     'times, but was unable to collect payment. Your '
                     'account has been downgraded to a free Demo plan. Only '
                     'the ten most recent episodes from each of your podcasts '
                     'will be shown to your listeners. All recurring tip '
                     'subscriptions to your podcasts have also been '
                     'cancelled.\n\nNo content or settings have been deleted '
                     'from your account. If you wish to re-subscribe, you may '
                     'do so at any time at the URL below.\n\n%s') %
                (BASE_URL + reverse('upgrade')))
    else:
        send_notification_email(
            user,
            ugettext('Payment failed for Pinecast subscription'),
            ugettext('Pinecast attempted to charge your payment card for your '
                     'current subscription, but was unable to collect payment. '
                     'If we fail to process your card three times, your '
                     'account will automatically be downgraded to a free Demo '
                     'plan.\n\n'
                     'No changes have currently been made to your account or '
                     'plan. Please update your payment information at the URL '
                     'below.\n\n%s') %
                (BASE_URL + reverse('dashboard') + '#settings,subscription'))
