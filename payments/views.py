import iso8601
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

import accounts.payment_plans as payment_plans
import views_tips
from .stripe_lib import stripe
from accounts.models import UserSettings
from dashboard.views import _pmrender
from pinecast.email import CONFIRMATION_PARAM
from pinecast.helpers import json_response, reverse
from podcasts.models import Podcast


@login_required
def upgrade(req):
    us = UserSettings.get_from_user(req.user)
    customer = us.get_stripe_customer()

    ctx = {'stripe_customer': customer}
    return _pmrender(req, 'payments/main.html', ctx)


def tips(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    us = UserSettings.get_from_user(pod.owner)
    if not us.stripe_payout_managed_account:
        redirect(pod.homepage)

    ctx = {'podcast': pod}
    if req.GET.get('error'):
        ctx['error'] = req.GET.get('error')

    if req.GET.get(CONFIRMATION_PARAM):
        return views_tips.create_session(req, ctx)

    if not req.session.get('pay_session'):
        return views_tips.no_session(req, ctx)

    return views_tips.tip_flow(req, ctx)


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

    new_plan_val = AVAILABLE_PLANS[new_plan]
    existing_subs = customer.subscriptions.all(limit=1)['data']

    # Handle downgrades to free
    if new_plan_val == payment_plans.PLAN_DEMO:
        if existing_subs:
            existing_sub = existing_subs[0]
            existing_sub.delete()
        us.plan = payment_plans.PLAN_DEMO
        us.save()
        return redirect('upgrade')

    plan_stripe_id = payment_plans.STRIPE_PLANS[new_plan_val]

    if existing_subs:
        existing_sub = existing_subs[0]
        existing_sub.plan = plan_stripe_id
        try:
            existing_sub.save()
        except Exception:
            return redirect('upgrade')
    else:
        try:
            sub = customer.subscriptions.create(plan=plan_stripe_id)
        except Exception:
            return redirect('upgrade')

    us.plan = new_plan_val
    us.save()

    return redirect('upgrade')


@require_POST
@login_required
@json_response
def set_payment_method(req):
    us = UserSettings.get_from_user(req.user)
    customer = us.get_stripe_customer()
    if customer:
        customer.source = req.POST.get('token')
        customer.save()
    else:
        us.create_stripe_customer(req.POST.get('token'))

    return {'success': True, 'id': us.stripe_customer_id}


@require_POST
@login_required
@json_response
def set_tip_cashout(req):
    try:
        dob = iso8601.parse_date(req.POST.get('dob'))
    except Exception:
        return {'success': False, 'error': 'invalid dob'}

    us = UserSettings.get_from_user(req.user)
    account = us.get_stripe_managed_account()
    if account:
        us.stripe_payout_managed_account = None
        us.save()
        account.delete()

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
    us.create_stripe_managed_account(
        req.POST.get('token'), ip, legal_entity)

    return {'success': True}
