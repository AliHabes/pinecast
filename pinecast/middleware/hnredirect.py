from __future__ import absolute_import

from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect

PREFERRED_HOSTNAME = 'pinecast.com'

class HostnameRedirect(object):

    def process_request(self, req):
        if settings.DEBUG:
            return None
        hostname = req.META.get('HTTP_HOST')
        if hostname == PREFERRED_HOSTNAME or hostname.endswith('.' + PREFERRED_HOSTNAME):
            return None

        return HttpResponsePermanentRedirect(
            'https://%s%s' % (PREFERRED_HOSTNAME, req.get_full_path()))
