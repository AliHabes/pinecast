import datetime
from functools import wraps

import bleach
import django.core.urlresolvers
import pytz
import requests
from django.conf import settings
from django.core.urlresolvers import reverse as reverse_django
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404 as dj_get_object_or_404


def json_response(*args, **jr_kwargs):
    def wrapper(view):
        @wraps(view)
        def func(*args, **kwargs):
            resp = view(*args, **kwargs)
            if not isinstance(resp, (dict, list, bool, str, unicode, int, float)):
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


def tz_offset(tz_name):
    offset = pytz.timezone(tz_name)._utcoffset
    return offset.seconds // 3600 + offset.days * 24


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
