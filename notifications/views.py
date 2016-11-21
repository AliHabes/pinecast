from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import NotificationHook
from accounts.models import Network, UserSettings
from accounts.payment_plans import FEATURE_MIN_NOTIFICATIONS, minimum
from pinecast.helpers import get_object_or_404, reverse
from podcasts.models import Podcast


NOTIFICATION_LIMIT = 30


def _get_podcast(req, **kwargs):
    podcast = get_object_or_404(Podcast, **kwargs)
    us = UserSettings.get_from_user(podcast.owner)
    if not minimum(us.plan, FEATURE_MIN_NOTIFICATIONS):
        raise HttpResponseForbidden()

    if req.user.is_staff:
        return podcast

    if req.user == podcast.owner:
        return podcast

    pods = Network.objects.filter(deactivated=False, members__in=[req.user], podcast__in=[podcast])
    if not pods.count():
        raise Http404()

    return podcast


@require_POST
@login_required
def new_notification(req):
    podcast = _get_podcast(req, id=req.POST.get('podcast'))
    if podcast.notifications.count() > NOTIFICATION_LIMIT:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast.slug) + '#settings,notifications')

    dest_type = req.POST.get('destination_type')
    dest = req.POST.get('destination_%s' % dest_type)
    trigger = req.POST.get('trigger')
    nh = NotificationHook(
        podcast=podcast,
        destination_type=dest_type,
        destination=dest,
        trigger=trigger,
        condition=req.POST.get('threshold') if trigger == 'listen_threshold' else None)
    nh.save()

    return redirect(reverse('podcast_dashboard', podcast_slug=podcast.slug) + '#settings,notifications')

@require_POST
@login_required
def delete_notification(req):
    podcast = _get_podcast(req, id=req.POST.get('podcast'))
    notification = get_object_or_404(NotificationHook, podcast=podcast, id=req.POST.get('id'))
    notification.delete()

    return redirect(reverse('podcast_dashboard', podcast_slug=podcast.slug) + '#settings,notifications')
