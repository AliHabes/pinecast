import json

import iso8601
import rollbar
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

    us = UserSettings.get_from_user(req.user)
    customer = us.get_stripe_customer()
    if not customer or new_plan not in AVAILABLE_PLANS:
        return redirect('upgrade')

    orig_plan = us.plan
    new_plan_val = AVAILABLE_PLANS[new_plan]
    existing_subs = customer.subscriptions.all(limit=1)['data']

    # Handle downgrades to free
    if new_plan_val == payment_plans.PLAN_DEMO:
        if existing_subs:
            existing_sub = existing_subs[0]
            existing_sub.delete()

        for podcast in req.user.podcast_set.all():
            for tip in podcast.recurring_tips.all():
                tip.cancel()

        us.plan = payment_plans.PLAN_DEMO
        us.save()
        return redirect('upgrade')

    plan_stripe_id = payment_plans.STRIPE_PLANS[new_plan_val]

    if existing_subs:
        existing_sub = existing_subs[0]
        existing_sub.plan = plan_stripe_id
        try:
            existing_sub.save()
        except Exception as e:
            rollbar.report_message(str(e), 'error')
            return redirect('upgrade')
    else:
        try:
            sub = customer.subscriptions.create(plan=plan_stripe_id)
        except stripe.error.CardError:
            return redirect(reverse('upgrade') + '?error=card')
        except Exception as e:
            rollbar.report_message(str(e), 'error')
            return redirect('upgrade')

    us.plan = new_plan_val
    us.save()

    was_upgrade = payment_plans.PLAN_RANKS[orig_plan] <= new_plan_val
    send_notification_email(
        req.user,
        ugettext('Your account has been %s') %
        (ugettext('upgraded') if was_upgrade else ugettext('downgraded')),
        ugettext('''Your Pinecast account has been updated successfully.
Your account is now marked as "%s".

Please contact Pinecast support if you have any questions.''') %
        payment_plans.PLANS_MAP[new_plan_val])

    return redirect('upgrade')


@require_POST
@login_required
def set_payment_method_redir(req):
    us = UserSettings.get_from_user(req.user)
    customer = us.get_stripe_customer()
    try:
        if customer:
            customer.source = req.POST.get('token')
            customer.save()
        else:
            us.create_stripe_customer(req.POST.get('token'))
    except stripe.error.CardError as e:
        return redirect(reverse('dashboard') + '?error=crej#settings')
    except Exception as e:
        rollbar.report_message(str(e), 'error')
        return redirect(reverse('dashboard') + '?error=cerr#settings')

    return redirect(reverse('dashboard') + '?success=csuc#settings')


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
        event = stripe.Event.retrieve(body['id'])
    except Exception:
        return HttpResponse(status=400)

    if event.type != 'invoice.payment_succeeded':
        return HttpResponse(status=200)

    try:
        sub = RecurringTip.objects.get(
            stripe_subscription_id=event.data.object.subscription)
    except RecurringTip.DoesNotExist:
        return HttpResponse(status=200)

    amount = event.data.object.total
    pod = sub.podcast

    tip_event = TipEvent(
        tipper=sub.tipper,
        podcast=pod,
        amount=amount,
        recurring_tip=sub)
    tip_event.save()

    pod.total_tips += amount
    pod.save()

    return HttpResponse(status=200)
