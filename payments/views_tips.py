from urllib import quote

import rollbar
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext
from django.views.decorators.http import require_POST

from .models import RecurringTip, TipEvent, TipUser
from .stripe_lib import stripe
from accounts.payment_plans import PLAN_DEMO, PLAN_TIP_LIMITS
from accounts.models import UserSettings
from dashboard.views import _pmrender
from pinecast.email import (CONFIRMATION_PARAM,
                            send_anon_confirmation_email as send_email,
                            send_notification_email,
                            validate_confirmation)
from pinecast.helpers import get_object_or_404, json_response, reverse
from podcasts.models import Podcast


def tip_flow(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    us = UserSettings.get_from_user(pod.owner)
    if not us.stripe_payout_managed_account:
        if pod.homepage:
            return redirect(pod.homepage)
        else:
            raise Http404()

    recurring_tip = None
    pay_session = req.session.get('pay_session')
    if pay_session:
        try:
            tipper = TipUser.objects.get(id=pay_session)
            recurring_tip = RecurringTip.objects.get(
                podcast=pod, tipper=tipper, deactivated=False)
        except Exception as e:
            raise e

    ctx = {'error': req.GET.get('error'),
           'recurring_tip': recurring_tip,
           'podcast': pod,
           'user': {'email': None}}

    return _pmrender(req, 'payments/tip_jar/main.html', ctx)


@require_POST
@json_response
def send_tip(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)

    try:
        amount = int(float(req.POST.get('amount')) / 100.0) * 100
        if amount < 100:
            return {'error': ugettext('Tips less than $1 are not allowed.')}
    except Exception:
        return HttpResponse(status=400)

    tip_type = req.POST.get('type')

    owner_us = UserSettings.get_from_user(pod.owner)
    if owner_us.plan == PLAN_DEMO and tip_type == 'subscribe':
        return {'error': ugettext('You cannot have recurring tips for free podcasts.')}

    if amount > PLAN_TIP_LIMITS[owner_us.plan]:
        return {'error': ugettext('That tip is too large for %s') % pod.name}


    if tip_type == 'charge':
        return _send_one_time_tip(req, pod, owner_us, amount)
    elif tip_type == 'subscribe':
        return _auth_subscription(req, pod, amount)
    else:
        return HttpResponse(status=400)


def _send_one_time_tip(req, podcast, owner_us, amount):
    email = req.POST.get('email')
    token = req.POST.get('token')

    tip_user = TipUser.tip_user_from(email_address=email)

    application_fee = int(amount * 0.05) if owner_us.plan == PLAN_DEMO else 0
    try:
        stripe_charge = stripe.Charge.create(
            amount=amount,
            application_fee=application_fee,
            currency='usd',
            description='Tip for %s' % podcast.name,
            destination=owner_us.stripe_payout_managed_account,
            source=token,
        )

    except Exception as e:
        rollbar.report_message('Error when sending tip: %s' % str(e), 'error')
        return {'error': str(e)}

    podcast.total_tips += amount
    podcast.save()

    tip_event = TipEvent(
        tipper=tip_user,
        podcast=podcast,
        amount=amount,
        fee_amount=application_fee,
        stripe_charge=stripe_charge.id)
    tip_event.save()

    send_notification_email(
        None,
        ugettext('Thanks for leaving a tip!'),
        ugettext('Your tip was sent: %s received $%0.2f. Thanks for supporting your '
                 'favorite content creators!') %
            (podcast.name, float(amount) / 100),
        email=email)
    send_notification_email(
        podcast.owner,
        ugettext('Your podcast was tipped!'),
        ugettext('%s received a tip of $%0.2f from %s. You should send them an email '
                 'thanking them for their generosity.') % (
            podcast.name, float(amount) / 100, tip_user.email_address))

    return {'success': True}


def _auth_subscription(req, podcast, amount):
    email = req.POST.get('email')
    token = req.POST.get('token')

    if not email:
        return {'error': ugettext('No valid email address was found.')}

    # Create the tip user if it doesn't already exist
    TipUser.tip_user_from(email_address=email)

    send_email(
        email,
        ugettext('Confirm your subscription for %s') % podcast.name,
        ugettext(
            'Thanks for pledging your support for %s at %0.2f every month! '
            'To finish the process and activate your subscription, click the '
            'link below. The link in this email will expire after one day.\n\n'
            'If you did not request this, you can ignore this email.' %
                (podcast.name, float(amount) / 100)),
        reverse('tip_jar_confirm_sub', podcast_slug=podcast.slug) +
            '?email=%s&token=%s&amount=%d' %
                (quote(email), quote(token), amount))

    return {'success': True}


def confirm_sub(req, podcast_slug):
    if not validate_confirmation(req):
        return _pmrender(req, 'payments/tip_jar/bad_link.html', ctx)

    # TODO: confirm that the podcast can receive subscriptions
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    owner_us = UserSettings.get_from_user(pod.owner)
    if (not owner_us.stripe_payout_managed_account or
        owner_us.plan == PLAN_DEMO):
        return HttpResponse(status=400)

    amount = int(req.GET.get('amount'))
    email = req.GET.get('email')
    token = req.GET.get('token')

    tip_user = TipUser.tip_user_from(email_address=email, auto_save=False)
    if not tip_user.verified:
        tip_user.verified = True
        tip_user.save()

    req.session['pay_session'] = tip_user.id

    # If the user already has a subscription, update it instead of billing them
    # with a new one.
    try:
        sub = RecurringTip.objects.get(tipper=tip_user, podcast=pod, deactivated=False)
        if sub.amount == amount:
            return redirect('tip_jar_subs')

        # Update Stripe with the new amount
        sub_obj = sub.get_subscription()
        sub_obj.amount = amount
        sub_obj.save()

        # Update the DB with the new amount
        old_amount = sub.amount
        sub.amount = amount
        sub.save()

        if amount > old_amount:
            pod.total_tips += amount - old_amount
            pod.save()

        return redirect('tip_jar_subs')
    except RecurringTip.DoesNotExist:
        pass

    managed_account = owner_us.stripe_payout_managed_account

    # Check that the tip sub plan exists
    plans = stripe.Plan.list(stripe_account=managed_account)
    if not plans.data:
        stripe.Plan.create(
            amount=100,
            currency='usd',
            id='tipsub',
            interval='month',
            name='Podcast Tip Jar',
            statement_descriptor='PODCAST TIP JAR',
            stripe_account=managed_account)

    # Create the customer associated with the managed account
    sub = RecurringTip(tipper=tip_user, podcast=pod, amount=amount)
    customer = stripe.Customer.create(
        email=email,
        plan='tipsub',
        quantity=amount / 100,
        source=token,
        stripe_account=managed_account)
    sub.stripe_customer_id = customer.id
    sub.stripe_subscription_id = customer.subscriptions.data[0].id
    sub.save()

    tip_event = TipEvent(
        tipper=tip_user,
        podcast=pod,
        amount=amount,
        recurring_tip=sub)
    tip_event.save()

    pod.total_tips += amount
    pod.save()

    send_notification_email(
        None,
        ugettext('Thanks for leaving a tip!'),
        ugettext('Your tip was sent: %s received $%0.2f. Thanks for supporting your '
                 'favorite content creators!') % (pod.name, float(amount) / 100),
        email=email)
    send_notification_email(
        pod.owner,
        ugettext('Someone subscribed to your podcast!'),
        ugettext('%s received a tip of $%0.2f from %s. Their subscription will '
                 'pay out once every month. You should send them an email '
                 'thanking them for their generosity.') % (
            pod.name, float(amount) / 100, email))

    return redirect('tip_jar_subs')


def subscriptions(req):
    if not req.session.get('pay_session'):
        return redirect('tip_jar_login')

    tip_user = get_object_or_404(TipUser, id=req.session['pay_session'])
    ctx = {'tip_user': tip_user}
    return _pmrender(req, 'payments/tip_jar/subscriptions.html', ctx)


def subscriptions_login(req):
    email = req.GET.get('email', req.POST.get('email'))
    if req.GET.get(CONFIRMATION_PARAM):
        validated = validate_confirmation(req)
        if validated:
            try:
                tip_user = TipUser.objects.get(email=email)
            except TipUser.DoesNotExist:
                # Verified because they just confirmed their email
                tip_user = TipUser(email=email, verified=True)
                tip_user.save()

            req.session['pay_session'] = tip_user.id
            return redirect('tip_jar_subs')
        # fallthrough

    if not req.POST:
        return _pmrender(req, 'payments/tip_jar/login.html')

    send_email(
        req.POST.get('email'),
        ugettext('Podcast Tip Jar - Email Verification'),
        ugettext(
            'Thanks for verifying your email! Click the link below '
            'to see your podcast subscriptions.'),
        reverse('tip_jar_login') + '?email=%s' % quote(email))

    return _pmrender(req, 'payments/tip_jar/check_email.html')


@require_POST
def cancel_sub(req, podcast_slug):
    if not req.session.get('pay_session'):
        return redirect('tip_jar_login')

    try:
        pod = Podcast.objects.get(slug=podcast_slug)
    except Podcast.DoesNotExist:
        return redirect('tip_jar_subs')

    tipper = TipUser.objects.get(id=req.session['pay_session'])

    try:
        recurring_tip = RecurringTip.objects.get(tipper=tipper, podcast=pod, deactivated=False)
    except RecurringTip.DoesNotExist:
        return redirect('tip_jar_subs')

    recurring_tip.cancel()

    return redirect('tip_jar_subs')
