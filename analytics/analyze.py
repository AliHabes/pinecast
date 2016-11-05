import base64
import datetime

from user_agents import parse


def get_device_type(req):
    parsed = _parse_req(req)
    settled = {
        'browser': parsed.browser.family,
        'device': parsed.device.family,
        'os': parsed.os.family,
    }
    ua = req.META.get('HTTP_USER_AGENT', 'Unknown')
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

    return settled['browser'], settled['device'], settled['os']


def is_bot(req):
    return _parse_req(req).is_bot


def _parse_req(req):
    if not hasattr(req, '__parsed_ua'):
        setattr(req, '__parsed_ua', parse(req.META.get('HTTP_USER_AGENT', 'Unknown')))
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
