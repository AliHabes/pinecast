from __future__ import absolute_import

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

import accounts.payment_plans as payment_plans
from .models import Collaborator
from .views import get_podcast
from accounts.decorators import restrict_minimum_plan
from pinecast.helpers import reverse


@login_required
@require_POST
@restrict_minimum_plan(payment_plans.FEATURE_MIN_COLLABORATORS)
def new_collaborator(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)
    if pod.owner != req.user and not req.user.is_staff:
        raise Http404

    try:
        user = User.objects.get(email__iexact=req.POST.get('email'))
    except User.DoesNotExist:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '?collaberr=collab_dne#settings,collabs')

    if req.user == user:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '?collaberr=yourself#settings,collabs')

    if Collaborator.objects.filter(collaborator=user, podcast=pod).exists():
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#settings,collabs')

    c = Collaborator(podcast=pod, collaborator=user)
    c.save()

    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#settings,collabs')


@login_required
@require_POST
@restrict_minimum_plan(payment_plans.FEATURE_MIN_COLLABORATORS)
def delete_collaborator(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)
    if pod.owner != req.user and not req.user.is_staff:
        raise Http404

    try:
        c = Collaborator.objects.get(id=req.POST.get('id'))
        if c.podcast != pod:
            raise Http404
        c.delete()
    except Collaborator.DoesNotExist:
        pass

    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#settings,collabs')
