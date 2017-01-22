from __future__ import absolute_import

from django.conf import settings
from influxdb import InfluxDBClient

from pinecast.types import StringTypes


def get_client():
    return InfluxDBClient(
        host=settings.INFLUXDB_HOST,
        port=settings.INFLUXDB_PORT,
        username=settings.INFLUXDB_USERNAME,
        password=settings.INFLUXDB_PASSWORD,
        ssl=settings.INFLUXDB_SSL,
        verify_ssl=settings.INFLUXDB_SSL,
        timeout=10)


def escape(val):
    if isinstance(val, StringTypes):
        return "'%s'" % val.replace("'", "\\'")
    elif isinstance(val, (int, float)):
        return str(val)

    raise Exception('Unknown type %s' % type(val))

def ident(val):
    return '"%s"' % val.replace('"', '\\"')
