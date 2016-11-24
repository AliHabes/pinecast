from __future__ import absolute_import

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import ugettext

import accounts.payment_plans as plans
import analytics.analyze as analyze
from .models import Feedback
from accounts.models import UserSettings
from dashboard.views import _pmrender
from notifications.models import NotificationHook
from pinecast.email import send_notification_email
from pinecast.helpers import get_object_or_404, reverse, validate_recaptcha
from podcasts.models import Podcast, PodcastEpisode


def podcast_comment_box(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    if not UserSettings.user_meets_plan(pod.owner, plans.FEATURE_MIN_COMMENT_BOX):
        raise Http404()
    if not req.POST:
        return _pmrender(req, 'feedback/comment_podcast.html', {'podcast': pod})

    try:
        if not _validate_recaptcha(req):
            raise Exception('Invalid ReCAPTCHA')

        ip = analyze.get_request_ip(req)
        f = Feedback(
            podcast=pod,
            sender=req.POST.get('email'),
            message=req.POST.get('message'),
            sender_ip=ip
        )
        f.save()
        send_notification_email(
            pod.owner,
            ugettext('[Pinecast] You got some feedback!'),
            'Go check the Feedback page of your podcast, %s, to see what was written.\n\n'
            'https://pinecast.com%s' %
            (pod.name,
             reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#tab-feedback')
        )

        NotificationHook.trigger_notification(
            podcast=pod,
            trigger_type='feedback',
            data={'content': req.POST.get('message'), 'sender': req.POST.get('email')})
    except Exception:
        return _pmrender(req, 'feedback/comment_podcast.html',
                         {'podcast': pod, 'error': True, 'default': req.POST})

    return _pmrender(req, 'feedback/thanks.html', {'podcast': pod})


def ep_comment_box(req, podcast_slug, episode_id):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    if not UserSettings.user_meets_plan(pod.owner, plans.FEATURE_MIN_COMMENT_BOX):
        raise Http404()
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=episode_id)
    if not req.POST:
        return _pmrender(req, 'feedback/comment_episode.html', {'podcast': pod, 'episode': ep})

    try:
        if not _validate_recaptcha(req):
            raise Exception('Invalid ReCAPTCHA')

        ip = analyze.get_request_ip(req)
        f = Feedback(
            podcast=pod,
            episode=ep,
            sender=req.POST.get('email'),
            message=req.POST.get('message'),
            sender_ip=ip
        )
        f.save()
        send_notification_email(
            pod.owner,
            ugettext('[Pinecast] You got some feedback!'),
            'Go check the Feedback page of %s--an episode on %s--to see what was written.\n\n'
            'https://pinecast.com%s' %
            (ep.title,
             pod.name,
             reverse('podcast_episode',
                     podcast_slug=podcast_slug,
                     episode_id=str(ep.id)) +
             '#tab-feedback')
        )
        NotificationHook.trigger_notification(
            podcast=pod,
            trigger_type='feedback',
            data={'episode': ep, 'content': req.POST.get('message'), 'sender': req.POST.get('email')})
    except Exception:
        return _pmrender(req, 'feedback/comment_episode.html',
                         {'podcast': pod, 'episode': ep, 'error': True, 'default': req.POST})

    return _pmrender(req, 'feedback/thanks.html', {'podcast': pod})


def _validate_recaptcha(req):
    if settings.DEBUG:
        return True
    response = req.POST.get('g-recaptcha-response')
    ip = analyze.get_request_ip(req)
    return validate_recaptcha(response, ip)
