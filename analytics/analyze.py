from __future__ import absolute_import

import base64
import hashlib
import datetime

from user_agents import parse


bot_browsers = (
    'Apache-HttpClient',
    'FacebookBot',
    'CFNetwork',
    'okhttp',
)
linux_oss = (
    'Fedora',
    'CentOS',
    'FreeBSD',
    'Kubuntu',
    'Linux',
    'Solaris',
    'Ubuntu',
)

def get_device_type(req=None, ua=None):
    if req and not hasattr(req, '__is_fake__'):
        # TODO: clean this up
        ua = req.META.get('HTTP_USER_AGENT', 'Unknown')
        parsed = _parse_req(req)
    else:
        parsed = parse(ua or 'Unknown')

    settled = {
        'browser': parsed.browser.family,
        'device': parsed.device.family,
        'os': parsed.os.family,
    }
    sb = settled['browser']
    if 'iTunes' in ua:
        settled['browser'] = 'itunes'
    elif 'Pocket Casts' in ua:
        settled['browser'] = 'pocketcasts'
    elif 'Miro' in ua:
        settled['browser'] = 'miro'
    elif 'BeyondPod' in ua:
        settled['browser'] = 'beyondpod'
    elif 'Overcast' in ua:
        settled['browser'] = 'overcast'
    elif 'Downcast' in ua:
        settled['browser'] = 'downcast'
    elif 'DoggCatcher' in ua:
        settled['browser'] = 'doggcatcher'
    elif any(x in sb for x in bot_browsers):
        settled['browser'] = 'server'
        settled['os'] = 'Other'
    elif 'Chrome' in sb or 'Chromium' in sb:
        settled['browser'] = 'chrome'
    elif 'Firefox' in sb or 'Iceweasel' in sb or 'SeaMonkey' in sb:
        settled['browser'] = 'firefox'
    elif 'Safari' in sb or 'WebKit' in sb:
        settled['browser'] = 'safari'
    elif 'Opera' in sb:
        settled['browser'] = 'opera'

    if 'Windows' in settled['os']:
        settled['os'] = 'Windows'
    elif any(x in settled['os'] for x in linux_oss):
        settled['os'] = 'Linux'

    return settled['browser'], settled['device'], settled['os']


def is_bot(req=None, ua=None):
    if not req and not ua: return False
    return (_parse_req(req) if req else parse(ua)).is_bot


def _parse_req(req):
    if not hasattr(req, '__parsed_ua'):
        ua = req.META.get('HTTP_USER_AGENT', 'Unknown') or 'Unknown'
        setattr(req, '__parsed_ua', parse(ua))
    return getattr(req, '__parsed_ua')


def get_request_ip(req):
    cf_ip = req.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        return cf_ip

    x_forwarded_for = req.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return req.META.get('REMOTE_ADDR')


def get_request_hash(req):
    ua = req.META.get('HTTP_USER_AGENT', 'Unknown')
    ip = get_request_ip(req)
    return get_raw_request_hash(ua, ip, datetime.date.today())

def get_raw_request_hash(ua, ip, ts):
    return base64.b64encode('%s:%s:%s' % (ts.isoformat(), ip, ua))

def get_ts_hash(ip, ua, ts):
    h = hashlib.sha1(','.join([ip, ua, ts.isoformat()])).hexdigest()
    # This allows one hour of timestamp variability
    return int(h, 16) % (1000000 * 60 * 60)
