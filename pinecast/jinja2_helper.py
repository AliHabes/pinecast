import datetime
import hashlib
import json
import string

import gfm
import jinja2
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.translation import ugettext, ugettext_lazy, ungettext
from jinja2 import Environment, evalcontextfilter

import accounts.payment_plans as payment_plans
import helpers
from accounts.models import UserSettings


def environment(**options):
    options['autoescape'] = True

    # Enable localization
    options.setdefault('extensions', [])
    if 'jinja2.ext.i18n' not in options['extensions']:
        options['extensions'].append('jinja2.ext.i18n')

    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,

        'dir': dir,
        'float': float,
        'int': int,
        'len': len,
        'now': lambda: datetime.datetime.now(),
        'sorted': sorted,
        'str': str,
        'url': helpers.reverse,
        'gravatar': gravatar,
        'getattr': getattr,

        '_': ugettext,
        'gettext': ugettext,
        'ngettext': ungettext,
        'get_user_settings': UserSettings.get_from_user,
        'minimum_plan': minimum_plan,
        'PLAN_NAMES': payment_plans.PLANS_MAP,
        'PLANS': payment_plans.PLANS_RAW,
        'PLAN_MAX_FILE_SIZE': payment_plans.MAX_FILE_SIZE,

        'SUPPORT_URL': settings.SUPPORT_URL,
        'RECAPTCHA_KEY': settings.RECAPTCHA_KEY,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,

        'timezones': [
            -12.0,
            -11.0,
            -10.0,
            # -9.5,
            -9.0,
            -8.0,
            -7.0,
            -6.0,
            -6.0,
            -5.0,
            -4.0,
            # -3.5,
            -3.0,
            -2.0,
            -1.0,
            0,
            1.0,
            2.0,
            3.0,
            # 3.5,
            4.0,
            # 4.5,
            5.0,
            # 5.5,
            6.0,
            # 6.5,
            7.0,
            8.0,
            # 8.5,
            # 8.75,
            9.0,
            # 9.5,
            10.0,
            # 10.5,
            11.0,
            12.0,
            # 12.75,
            13.0,
            14.0,
        ],
    })
    env.filters['format_tz'] = format_tz
    env.filters['https'] = lambda s: ('https:%s' % s[5:]) if s.startswith('http:') else s
    env.filters['json'] = json.dumps
    env.filters['safe_json'] = safe_json
    env.filters['markdown'] = gfm.markdown
    env.filters['pretty_date'] = pretty_date
    env.filters['sanitize'] = helpers.sanitize
    env.filters['replace'] = string.replace
    return env


TZ_SHORTHAND = {
    -8.0: ugettext_lazy('PST'),
    -7.0: ugettext_lazy('MST'),
    -6.0: ugettext_lazy('CST'),
    -5.0: ugettext_lazy('EST'),
}

def format_tz(tz):
    if tz == 0:
        return 'UTC'
    offset = '%d:%0.2d' % (abs(int(tz)), tz % 1 * 60)
    sign = '+' if tz > 0 else '-'
    return 'UTC%s%s%s' % (sign, offset, ' (%s)' % TZ_SHORTHAND[tz] if tz in TZ_SHORTHAND else '')

def minimum_plan(user_settings, plan):
    if isinstance(user_settings, User):
        user_settings = UserSettings.get_from_user(user_settings)
    return payment_plans.minimum(user_settings.plan, plan)


def gravatar(s, size=40):
    dig = hashlib.md5(s).hexdigest()
    return 'https://www.gravatar.com/avatar/%s?s=%d' % (dig, size)


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
                return ungettext('{n} minute from now', '{n} minutes from now', second_diff / 60).format(n=second_diff / 60)
            if second_diff < 7200:
                return ugettext('in an hour')
            if second_diff < 86400:
                return ungettext('{n} hour from now', '{n} hours from now', second_diff / 3600).format(n=second_diff / 3600)
        day_diff += 1
        if day_diff == 1:
            return ugettext('tomorrow')
        if day_diff < 7:
            return ungettext('{n} day from now', '{n} days from now', day_diff).format(n=day_diff)
        if day_diff < 31:
            return ungettext('{n} week from now', '{n} weeks from now', day_diff / 7).format(n=day_diff / 7)
        if day_diff < 365:
            return ungettext('{n} month from now', '{n} months from now', day_diff / 30).format(n=day_diff / 30)
        return ungettext('{n} year from now', '{n} years from now', day_diff / 365).format(n=day_diff / 365)

    if day_diff == 0:
        if second_diff < 10:
            return ugettext('just now')
        if second_diff < 60:
            return ungettext('{n} second ago', '{n} seconds ago', second_diff).format(n=second_diff)
        if second_diff < 120:
            return ugettext('a minute ago')
        if second_diff < 3600:
            return ungettext('{n} minute ago', '{n} minutes ago', second_diff / 60).format(n=second_diff / 60)
        if second_diff < 7200:
            return ugettext('an hour ago')
        if second_diff < 86400:
            return ungettext('{n} hour ago', '{n} hours ago', second_diff / 3600).format(n=second_diff / 3600)
    if day_diff == 1:
        return ugettext('yesterday')
    if day_diff < 7:
        return ungettext('{n} day ago', '{n} days ago', day_diff).format(n=day_diff)
    if day_diff < 31:
        return ungettext('{n} week ago', '{n} weeks ago', day_diff / 7).format(n=day_diff / 7)
    if day_diff < 365:
        return ungettext('{n} month ago', '{n} months ago', day_diff / 30).format(n=day_diff / 30)
    return ungettext('{n} year ago', '{n} years ago', day_diff / 365).format(n=day_diff / 365)


def safe_json(data):
    if data is None:
        return 'null'
    elif isinstance(data, bool):
        return 'true' if data else 'false'
    elif isinstance(data, (int, long, float)):
        return str(data)
    elif isinstance(data, (tuple, list)):
        return jinja2.Markup('[%s]' % ','.join(safe_json(x) for x in data))
    elif isinstance(data, dict):
        return jinja2.Markup('{%s}' % ','.join(
            '%s:%s' % (safe_json(key), safe_json(val)) for key, val in data.items()))
    safe_data = str(jinja2.escape(data))
    return jinja2.Markup(json.dumps(safe_data))
