import base64
import collections
import datetime
import hashlib
import hmac
import json
import time
import urllib
import uuid

import itsdangerous
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import ugettext
from django.views.decorators.http import require_GET, require_POST

import accounts.payment_plans as payment_plans
import analytics.query as analytics_query
import pinecast.constants as constants
from accounts.decorators import restrict_minimum_plan
from accounts.models import Network, UserSettings
from feedback.models import Feedback, EpisodeFeedbackPrompt
from pinecast.helpers import get_object_or_404, json_response, reverse
from podcasts.models import (CATEGORIES, Podcast, PodcastCategory,
                             PodcastEpisode)
from sites.models import Site


signer = itsdangerous.Signer(settings.SECRET_KEY)


def _pmrender(req, template, data=None):
    data = data or {}

    class DefaultEmptyDict(collections.defaultdict):
        def __init__(self):
            super(DefaultEmptyDict, self).__init__(lambda: '')

        def get(self, _, d=''):
            return d

    data.setdefault('settings', settings)
    data.setdefault('default', DefaultEmptyDict())
    data['sign'] = lambda x: signer.sign(x) if x else x
    if not req.user.is_anonymous():
        data.setdefault('user', req.user)

        networks = req.user.network_set.filter(deactivated=False)
        data.setdefault('networks', networks)

        podcasts = list(set(
            req.user.podcast_set.all() | Podcast.objects.filter(networks__in=networks)))
        data.setdefault('podcasts', podcasts)

        uset = UserSettings.get_from_user(req.user)
        data.setdefault('user_settings', uset)
        data.setdefault('tz_delta', uset.get_tz_delta())
        data.setdefault('max_upload_size', payment_plans.MAX_FILE_SIZE[uset.plan])

    data['is_admin'] = req.user.is_staff and bool(req.GET.get('admin'))

    return render(req, template, data)


class EmptyStringDefaultDict(collections.defaultdict):
    def __init__(self):
        super(EmptyStringDefaultDict, self).__init__(lambda: '')

    def get(self, key, def_=None):
        out = super(EmptyStringDefaultDict, self).get(key, def_)
        return out if out is not None else ''


def get_podcast(req, slug):  # TODO: move to the Podcast model
    try:
        pod = Podcast.objects.get(slug=slug)
    except Podcast.DoesNotExist:
        raise Http404()

    if req.user.is_staff:  # Admins should be able to see everything
        return pod

    if pod.owner == req.user:
        return pod
    pods = Network.objects.filter(deactivated=False, members__in=[req.user], podcast__in=[pod])
    if not pods.count():
        raise Http404()

    return pod


@login_required
def dashboard(req):
    ctx = {
        'success': req.GET.get('success'),
        'error': req.GET.get('error'),
    }
    return _pmrender(req, 'dashboard/dashboard.html', ctx)


MILESTONES = [1, 100, 250, 500, 1000, 2000, 5000, 7500, 10000, 15000, 20000,
              50000, 100000, 150000, 250000, 500000, 1000000, 2000000, 5000000,
              10000000, float('inf')]


@login_required
def podcast_dashboard(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)

    with analytics_query.AsyncContext() as async_ctx:
        total_listens = analytics_query.total_listens(pod, async_ctx)
        total_listens_this_week = analytics_query.total_listens_this_week(pod, async_ctx)
        subscribers = analytics_query.total_subscribers(pod, async_ctx)

    listens = total_listens()

    data = {
        'podcast': pod,
        'episodes': pod.podcastepisode_set.order_by('-publish'),
        'analytics': {
            'total_listens': listens,
            'total_listens_this_week': total_listens_this_week(),
            'subscribers': subscribers(),
        },
        'next_milestone': next(x for x in MILESTONES if x > listens),
        'previous_milestone': [x for x in MILESTONES if x <= listens][-1] if listens else 0,
        'hit_first_milestone': listens > MILESTONES[1],  # The first "real" milestone
        'is_still_importing': pod.is_still_importing(),

        'site': None,

        'LOCALES': constants.locales,
        'PODCAST_CATEGORIES': json.dumps(list(CATEGORIES)),
        'SITE_THEMES': Site.SITE_THEMES,
    }

    try:
        data['site'] = pod.site
    except Site.DoesNotExist:
        pass

    owner_uset = UserSettings.get_from_user(pod.owner)
    if payment_plans.minimum(owner_uset.plan, payment_plans.FEATURE_MIN_COMMENT_BOX):
        all_feedback = Feedback.objects.filter(podcast=pod)
        data['feedback_all'] = all_feedback
        data['feedback'] = all_feedback.filter(episode=None).order_by('-created')
        data['feedback_episodes'] = all_feedback.exclude(episode=None).annotate(
            Count('episode', distinct=True))

    return _pmrender(req, 'dashboard/podcast/page_podcast.html', data)

@login_required
def new_podcast(req):
    uset = UserSettings.get_from_user(req.user)
    if payment_plans.has_reached_podcast_limit(uset):
        return _pmrender(req, 'dashboard/podcast/page_new_upgrade.html')

    ctx = {
        'LOCALES': constants.locales,
        'PODCAST_CATEGORIES': json.dumps(list(CATEGORIES)),

        'reached_podcast_limit': payment_plans.has_reached_podcast_limit(uset)
    }

    if not req.POST:
        return _pmrender(req, 'dashboard/podcast/page_new.html', ctx)

    # Basic validation
    if (not req.POST.get('slug') or not req.POST.get('name')):
        ctx.update(default=req.POST, error=True)
        return _pmrender(req, 'dashboard/podcast/page_new.html', ctx)

    try:
        pod = Podcast(
            slug=req.POST.get('slug'),
            name=req.POST.get('name'),
            subtitle=req.POST.get('subtitle'),
            cover_image=signer.unsign(req.POST.get('image-url')),
            description=req.POST.get('description'),
            is_explicit=req.POST.get('is_explicit', 'false') == 'true',
            homepage=req.POST.get('homepage'),
            language=req.POST.get('language'),
            copyright=req.POST.get('copyright'),
            author_name=req.POST.get('author_name'),
            owner=req.user)
        pod.clean()
        pod.save()
    except Exception as e:
        ctx.update(default=req.POST, error=True)
        return _pmrender(req, 'dashboard/podcast/page_new.html', ctx)

    try:
        pod.set_category_list(req.POST.get('categories'))
    except Exception:
        pass

    return redirect('podcast_dashboard', podcast_slug=pod.slug)


@require_POST
@login_required
def edit_podcast(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)

    ctx = {'podcast': pod,
           'PODCAST_CATEGORIES': json.dumps(list(CATEGORIES))}

    try:
        pod.name = req.POST.get('name')
        pod.subtitle = req.POST.get('subtitle')
        pod.description = req.POST.get('description')
        pod.is_explicit = req.POST.get('is_explicit', 'false') == 'true'
        pod.homepage = req.POST.get('homepage')
        pod.language = req.POST.get('language')
        pod.copyright = req.POST.get('copyright')
        pod.author_name = req.POST.get('author_name')
        pod.cover_image = signer.unsign(req.POST.get('image-url'))
        pod.set_category_list(req.POST.get('categories'))
        pod.full_clean()
        pod.save()
    except Exception as e:
        return redirect(reverse('podcast_dashboard', podcast_slug=pod.slug) + '?error=serr#settings')
    return redirect('podcast_dashboard', podcast_slug=pod.slug)


@require_POST
@login_required
def delete_podcast(req, podcast_slug):
    # This doesn't use `get_podcast` because only the owner may delete the podcast
    pod = get_object_or_404(Podcast, slug=podcast_slug, owner=req.user)

    for tip in pod.recurring_tips.all():
        tip.cancel()

    pod.delete()
    return redirect('dashboard')

@require_POST
@login_required
def delete_podcast_episode(req, podcast_slug, episode_id):
    pod = get_podcast(req, podcast_slug)
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=episode_id)
    ep.delete()
    return redirect('podcast_dashboard', podcast_slug=pod.slug)


@login_required
def podcast_new_ep(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)

    tz_delta = UserSettings.get_from_user(req.user).get_tz_delta()

    latest_episode = pod.get_most_recent_episode()
    ctx = {
        'podcast': pod,
        'latest_ep': latest_episode,
    }
    if not req.POST:
        base_default = EmptyStringDefaultDict()
        base_default['publish'] = datetime.datetime.strftime(
            datetime.datetime.now() + tz_delta,
            '%Y-%m-%dT%H:%M'  # 2015-07-09T12:00
        )
        ctx['default'] = base_default
        return _pmrender(req, 'dashboard/episode/page_new.html', ctx)

    try:
        naive_publish = datetime.datetime.strptime(req.POST.get('publish'), '%Y-%m-%dT%H:%M')  # 2015-07-09T12:00
        adjusted_publish = naive_publish - tz_delta

        image_url = req.POST.get('image-url')

        ep = PodcastEpisode(
            podcast=pod,
            title=req.POST.get('title'),
            subtitle=req.POST.get('subtitle'),
            publish=adjusted_publish,
            description=req.POST.get('description'),
            duration=int(req.POST.get('duration-hours')) * 3600 + int(req.POST.get('duration-minutes')) * 60 + int(req.POST.get('duration-seconds')),

            audio_url=signer.unsign(req.POST.get('audio-url')),
            audio_size=int(req.POST.get('audio-url-size')),
            audio_type=req.POST.get('audio-url-type'),

            image_url=signer.unsign(image_url) if image_url else pod.cover_image,

            copyright=req.POST.get('copyright'),
            license=req.POST.get('license'),

            explicit_override=req.POST.get('explicit_override'))
        ep.set_flair(req.POST, no_save=True)
        ep.save()
        if req.POST.get('feedback_prompt'):
            prompt = EpisodeFeedbackPrompt(episode=ep, prompt=req.POST.get('feedback_prompt'))
            prompt.save()
    except Exception as e:
        ctx['error'] = True
        ctx['default'] = req.POST
        return  _pmrender(req, 'dashboard/episode/page_new.html', ctx)
    return redirect('podcast_dashboard', podcast_slug=pod.slug)


@require_POST
@login_required
def edit_podcast_episode(req, podcast_slug, episode_id):
    pod = get_podcast(req, podcast_slug)
    ep = get_object_or_404(PodcastEpisode, id=episode_id, podcast=pod)

    try:
        naive_publish = datetime.datetime.strptime(req.POST.get('publish'), '%Y-%m-%dT%H:%M')  # 2015-07-09T12:00
        adjusted_publish = naive_publish - UserSettings.get_from_user(req.user).get_tz_delta()

        ep.title = req.POST.get('title')
        ep.subtitle = req.POST.get('subtitle')
        ep.publish = adjusted_publish
        ep.description = req.POST.get('description')
        ep.duration = int(req.POST.get('duration-hours')) * 3600 + int(req.POST.get('duration-minutes')) * 60 + int(req.POST.get('duration-seconds'))

        ep.audio_url = signer.unsign(req.POST.get('audio-url'))
        ep.audio_size = int(req.POST.get('audio-url-size'))
        ep.audio_type = req.POST.get('audio-url-type')

        image_url = req.POST.get('image-url')
        if image_url:
            ep.image_url = signer.unsign(req.POST.get('image-url'))
        else:
            ep.image_url = pod.cover_image

        ep.copyright = req.POST.get('copyright')
        ep.license = req.POST.get('license')

        ep.explicit_override = req.POST.get('explicit_override')

        ep.set_flair(req.POST, no_save=True)
        ep.save()

        ep.delete_feedback_prompt()
        if req.POST.get('feedback_prompt'):
            prompt = EpisodeFeedbackPrompt(episode=ep, prompt=req.POST.get('feedback_prompt'))
            prompt.save()

    except Exception as e:
        return redirect(reverse('podcast_episode', podcast_slug=pod.slug, episode_id=str(ep.id)) + '?error=true#edit')
    return redirect('podcast_episode', podcast_slug=pod.slug, episode_id=str(ep.id))

@require_POST
@login_required
def podcast_episode_publish_now(req, podcast_slug, episode_id):
    pod = get_podcast(req, podcast_slug)
    ep = get_object_or_404(PodcastEpisode, id=episode_id, podcast=pod)

    ep.publish = datetime.datetime.now()
    ep.save()

    return redirect('podcast_episode', podcast_slug=pod.slug, episode_id=str(ep.id))

@login_required
def podcast_episode(req, podcast_slug, episode_id):
    pod = get_podcast(req, podcast_slug)
    ep = get_object_or_404(PodcastEpisode, id=episode_id, podcast=pod)

    with analytics_query.AsyncContext() as async_ctx:
        total_listens = analytics_query.total_listens(
            pod, async_ctx, episode_id=str(ep.id))

    data = {
        'podcast': pod,
        'episode': ep,
        'analytics': {'total_listens': total_listens()},
        'feedback': Feedback.objects.filter(podcast=pod, episode=ep).order_by('-created'),
    }
    return _pmrender(req, 'dashboard/episode/page_episode.html', data)


@login_required
@json_response
def slug_available(req):
    try:
        Podcast.objects.get(slug=req.GET.get('slug'))
    except Podcast.DoesNotExist:
        return {'valid': True}
    else:
        return {'valid': False}


@login_required
@json_response
def get_upload_url(req, podcast_slug, type):
    if type not in ['audio', 'image']:
        return Http404('Type not recognized')

    pod = None

    # NOTE: When udating the code below, make sure to also update gc.py as well
    # to make sure that the cleanup script continues to work as expected.
    if not podcast_slug.startswith('$'):
        pod = get_podcast(req, podcast_slug)
        basepath = 'podcasts/%s/%s/' % (pod.id, type)
    elif podcast_slug == '$none':
        basepath = 'podcasts/covers/'
    elif podcast_slug == '$net':
        basepath = 'networks/covers/'
    elif podcast_slug == '$site':
        basepath = 'sites/'
    else:
        return Http404('Unknown slug')

    uid = str(uuid.uuid4())
    path = '%s%s/%s' % (basepath, uid, req.GET.get('name'))
    encoded_path = '%s%s/%s' % (basepath, uid, urllib.pathname2url(req.GET.get('name')))

    mime_type = req.GET.get('type')

    expires = int(time.time() + 60 * 60 * 24)
    amz_headers = 'x-amz-acl:public-read'

    uset = UserSettings.get_from_user(pod.owner if pod is not None else req.user)

    max_size = 1024 * 1024 * 2 if type == 'image' else payment_plans.MAX_FILE_SIZE[uset.plan]
    policy = {
        # hours=6 so users around midnight don't get screwed.
        'expiration': (datetime.datetime.now() + datetime.timedelta(days=1, hours=6)).strftime('%Y-%m-%dT00:00:00.000Z'),
        'conditions': [
            {'bucket': settings.S3_BUCKET},
            ['starts-with', '$key', basepath],
            {'acl': 'public-read'},
            {'Content-Type': mime_type},
            ['content-length-range', 0, max_size],
        ],
    }
    encoded_policy = base64.b64encode(json.dumps(policy))

    destination_url = 'https://%s.s3.amazonaws.com/%s' % (settings.S3_BUCKET, path)
    signed_dest_url = signer.sign(destination_url)
    return {
        'url': 'https://%s.s3.amazonaws.com/' % settings.S3_BUCKET,
        'method': 'post',
        'headers': {},
        'fields': {
            'key': path,
            'acl': 'public-read',
            'Content-Type': mime_type,
            'AWSAccessKeyId': settings.S3_ACCESS_ID,
            'Policy': encoded_policy,
            'Signature': base64.b64encode(hmac.new(settings.S3_SECRET_KEY.encode(),
                                                   encoded_policy.encode('utf8'),
                                                   hashlib.sha1).digest()),
        },
        'destination_url': signed_dest_url,
    }


@login_required
@restrict_minimum_plan(payment_plans.FEATURE_MIN_COMMENT_BOX)
def delete_comment(req, podcast_slug, comment_id):
    pod = get_podcast(req, podcast_slug)
    comment = get_object_or_404(Feedback, podcast=pod, id=comment_id)

    ep = comment.episode
    comment.delete()
    if ep:
        return redirect(
            reverse('podcast_episode', podcast_slug=podcast_slug, episode_id=str(ep.id)) + '#tab-feedback'
        )
    else:
        return redirect(
            reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#tab-feedback'
        )

@login_required
@require_GET
@json_response(safe=False)
def get_episodes(req):
    pod_slug = req.GET.get('podcast')
    network = req.GET.get('network_id')
    start_date = req.GET.get('start_date')

    if not pod_slug and not network:
        return []

    pods = set()
    if pod_slug:
        pods.add(get_podcast(req, pod_slug))

    if network:
        net = get_object_or_404(Network, id=network, members__in=[req.user])
        pods = pods | set(net.podcast_set.all())

    if not pods:
        return []

    query = PodcastEpisode.objects.filter(
        podcast__in=list(pods),
        publish__lt=datetime.datetime.now(),
        awaiting_import=False
    )
    if start_date:
        try:
            parsed_date = datetime.datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            raise Http404()
        query = query.filter(publish__gte=parsed_date)

    uset = UserSettings.get_from_user(req.user)
    tz_delta = uset.get_tz_delta()
    return [
        {'id': ep.id,
         'title': ep.title,
         'podcastSlug': ep.podcast.slug,
         'publish': (ep.publish + tz_delta).strftime('%Y-%m-%dT%H:%M:%S')} for
        ep in
        sorted(query, cmp=lambda a, b: cmp(a.publish, b.publish))
    ]
