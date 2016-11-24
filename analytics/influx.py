from __future__ import absolute_import

from django.conf import settings
from influxdb import InfluxDBClient


def get_client():
    return InfluxDBClient(
        host=settings.INFLUXDB_HOST,
        port=settings.INFLUXDB_PORT,
        username=settings.INFLUXDB_USERNAME,
        password=settings.INFLUXDB_PASSWORD,
        ssl=settings.INFLUXDB_SSL,
        verify_ssl=settings.INFLUXDB_SSL,
        timeout=10)
