from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

import accounts.payment_plans as payment_plans
from .views import get_podcast
from accounts.decorators import restrict_minimum_plan
from pinecast.helpers import reverse


@login_required
@require_POST
@restrict_minimum_plan(payment_plans.FEATURE_MIN_PRIVATE_EPS_OPTIONS)
def set_tip_jar_options(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)

    if req.POST.get('min_dollar_amount'):
        amount = int(req.POST.get('min_dollar_amount'))
        pod.private_access_min_subscription = max(min(amount, 5000), 100)
    else:
        pod.private_access_min_subscription = None

    if req.POST.get('enable_age'):
        pod.private_after_age = abs(int(req.POST.get('amount_age'))) * 86400
    else:
        pod.private_after_age = None

    if req.POST.get('enable_nth'):
        pod.private_after_nth = abs(int(req.POST.get('amount_nth')))
    else:
        pod.private_after_nth = None

    pod.save()

    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#settings,tip-jar')
