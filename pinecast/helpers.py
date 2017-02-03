import collections
import datetime
from functools import wraps

import bleach
import django.core.urlresolvers
import requests
from django.conf import settings
from django.core.urlresolvers import reverse as reverse_django
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404 as dj_get_object_or_404, render as dj_render
from django.utils.translation import ugettext, ungettext

from accounts import payment_plans
from pinecast.signatures import signer_nots
from pinecast.types import StringTypes


def json_response(*args, **jr_kwargs):
    def wrapper(view):
        @wraps(view)
        def func(*args, **kwargs):
            resp = view(*args, **kwargs)
            if not isinstance(resp, (dict, list, bool, int, float) + StringTypes) and resp is not None:
                # Handle HttpResponse/HttpResponseBadRequest/etc
                return resp
            return JsonResponse(resp, safe=jr_kwargs.get('safe', True))
        return func
    return wrapper if jr_kwargs else wrapper(*args)


@wraps(reverse_django)
def reverse(viewname, kwargs=None, **kw):
    if kwargs is None:
        kwargs = {}
    kwargs.update(kw)
    other_kw = {}
    if 'urlconf' in kwargs:
        other_kw['urlconf'] = kwargs['urlconf']
        del kwargs['urlconf']
    return reverse_django(viewname, kwargs=kwargs, **other_kw)


def cached_method(func):
    @wraps(func)
    def memoized(self, *args):
        cache = getattr(self, '__pccache__%s__' % func.__name__, None)
        if not cache:
            cache = {}
            setattr(self, '__pccache__%s__' % func.__name__, cache)

        targs = tuple(args)
        if targs not in cache:
            cache[targs] = func(self, *args)
        return cache[targs]
    return memoized


def sanitize(data):
    return bleach.clean(
        data,
        bleach.ALLOWED_TAGS + [
            'p', 'div', 'dl', 'dt', 'dd', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'span'],
        {'*': ['src', 'href', 'title']}
    )


def validate_recaptcha(response, ip):
    if settings.DEBUG:
        return True
    result = requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={'response': response,
              'secret': settings.RECAPTCHA_SECRET,
              'remoteip': ip})
    try:
        parsed = result.json()
    except Exception:
        return False

    return parsed['success']


def round_now():
    now = datetime.datetime.now()
    return now - datetime.timedelta(microseconds=now.microsecond)


def get_object_or_404(*args, **kwargs):
    try:
        return dj_get_object_or_404(*args, **kwargs)
    except ValueError:
        raise Http404()

def pretty_date(time=None):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.datetime.utcnow()
    if type(time) is int:
        diff = now - datetime.datetime.fromtimestamp(time)
    elif isinstance(time, datetime.datetime):
        diff = now - time
    elif isinstance(time, datetime.date):
        diff = now - datetime.datetime.combine(
            time, datetime.datetime.min.time())
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        day_diff *= -1
        day_diff -= 1
        second_diff *= -1
        second_diff += 86400
        if day_diff < 1:
            if second_diff < 10:
                return ugettext('imminently')
            if second_diff < 60:
                return ungettext('{n} second from now', '{n} seconds from now', second_diff).format(n=second_diff)
            if second_diff < 120:
                return ugettext('in a minute')
            if second_diff < 3600:
                return ungettext('{n} minute from now', '{n} minutes from now', second_diff // 60).format(n=second_diff // 60)
            if second_diff < 7200:
                return ugettext('in an hour')
            if second_diff < 86400:
                return ungettext('{n} hour from now', '{n} hours from now', second_diff // 3600).format(n=second_diff // 3600)
        day_diff += 1
        if day_diff == 1:
            return ugettext('tomorrow')
        if day_diff < 7:
            return ungettext('{n} day from now', '{n} days from now', day_diff).format(n=day_diff)
        if day_diff < 31:
            return ungettext('{n} week from now', '{n} weeks from now', day_diff // 7).format(n=day_diff // 7)
        if day_diff < 365:
            return ungettext('{n} month from now', '{n} months from now', day_diff // 30).format(n=day_diff // 30)
        return ungettext('{n} year from now', '{n} years from now', day_diff // 365).format(n=day_diff // 365)

    if day_diff == 0:
        if second_diff < 10:
            return ugettext('just now')
        if second_diff < 60:
            return ungettext('{n} second ago', '{n} seconds ago', second_diff).format(n=second_diff)
        if second_diff < 120:
            return ugettext('a minute ago')
        if second_diff < 3600:
            return ungettext('{n} minute ago', '{n} minutes ago', second_diff // 60).format(n=second_diff // 60)
        if second_diff < 7200:
            return ugettext('an hour ago')
        if second_diff < 86400:
            return ungettext('{n} hour ago', '{n} hours ago', second_diff // 3600).format(n=second_diff // 3600)
    if day_diff == 1:
        return ugettext('yesterday')
    if day_diff < 7:
        return ungettext('{n} day ago', '{n} days ago', day_diff).format(n=day_diff)
    if day_diff < 31:
        return ungettext('{n} week ago', '{n} weeks ago', day_diff // 7).format(n=day_diff // 7)
    if day_diff < 365:
        return ungettext('{n} month ago', '{n} months ago', day_diff // 30).format(n=day_diff // 30)
    return ungettext('{n} year ago', '{n} years ago', day_diff // 365).format(n=day_diff // 365)


def populate_context(user, ctx=None):
    ctx = ctx or {}
    if not user.is_anonymous():
        ctx['user'] = user

        if 'networks' not in ctx:
            networks = set(user.network_set.filter(deactivated=False))
            ctx['networks'] = networks
        else:
            networks = ctx['networks']

        if 'podcasts' not in ctx:
            from dashboard.models import Collaborator
            from podcasts.models import Podcast
            podcasts = set(
                user.podcast_set.all() |
                Podcast.objects.filter(networks__in=networks)
            )
            podcasts |= {x.podcast for x in Collaborator.objects.filter(collaborator=user).select_related('podcast')}
            ctx.setdefault('podcasts', sorted(podcasts, key=lambda p: p.name))

        if 'user_settings' not in ctx:
            from accounts.models import UserSettings
            uset = UserSettings.get_from_user(user)
            ctx['user_settings'] = uset
        else:
            uset = ctx['user_settings']

        if 'tz_delta' not in ctx:
            ctx['tz_delta'] = uset.get_tz_delta()

        ctx.setdefault('max_upload_size', payment_plans.MAX_FILE_SIZE[uset.plan])

    return ctx


def render(req, template, data=None):
    data = data or {}

    class DefaultEmptyDict(collections.defaultdict):
        def __init__(self):
            super(DefaultEmptyDict, self).__init__(lambda: '')

        def get(self, _, d=''):
            return d

    data.setdefault('settings', settings)
    data.setdefault('default', DefaultEmptyDict())
    data['sign'] = lambda x: signer_nots.sign(x.encode('utf-8')).decode('utf-8') if x else x
    populate_context(req.user, data)
    data['is_admin'] = req.user.is_staff and bool(req.GET.get('admin'))
    return dj_render(req, template, data)
