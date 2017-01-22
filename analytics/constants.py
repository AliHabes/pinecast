from __future__ import absolute_import

from datetime import datetime, timedelta

from django.conf import settings
from django.utils.translation import ugettext_lazy

from .influx import escape


TIME_MIN = '1677-09-21T00:12:43.145224194Z'

influx_databases = {
    'subscription': settings.INFLUXDB_DB_SUBSCRIPTION,
    'subscription-country': settings.INFLUXDB_DB_SUBSCRIPTION,
    'listen': settings.INFLUXDB_DB_LISTEN,
    'listen-country': settings.INFLUXDB_DB_LISTEN,
    'listen-platform': settings.INFLUXDB_DB_LISTEN,
    'notification': settings.INFLUXDB_DB_NOTIFICATION,
}

SOURCE_MAP = {
    'direct': ugettext_lazy('Direct'),
    'rss': ugettext_lazy('Subscription'),
    'embed': ugettext_lazy('Player'),
    None: ugettext_lazy('Unknown'),
}

def dtnow(tz):
    now = datetime.now()
    if not tz:
        return now
    return now - timedelta(hours=tz)

def ftime(ts):
    return escape(ts.isoformat() + 'Z')

USER_TIMEFRAMES = {
    'day': lambda tz: 'time >= %s' % ftime(dtnow(tz) - timedelta(days=1)),
    'yesterday':  lambda tz: 'time < %s AND time > %s' % (
        ftime(dtnow(tz) - timedelta(days=1)),
        ftime(dtnow(tz) - timedelta(days=2))),
    'week': lambda tz: 'time >= %s' % ftime(dtnow(tz) - timedelta(days=7)),
    'month': lambda tz: 'time >= %s' % ftime(dtnow(tz) - timedelta(days=30)),
    'sixmonth': lambda tz: 'time >= %s' % ftime(dtnow(tz) - timedelta(days=30 * 6)),
    'year': lambda tz: 'time >= %s' % ftime(dtnow(tz) - timedelta(days=365)),
    'all': lambda tz: 'time >= \'%s\'' % TIME_MIN,
}
