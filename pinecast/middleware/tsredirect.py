from django.conf import settings
from django.core.urlresolvers import is_valid_path
from django.http import HttpResponsePermanentRedirect


class TrailingSlashRedirect(object):
    def process_request(self, req):
        scheme = 'http:' if settings.DEBUG else 'https:'
        path = req.get_full_path()
        if path.endswith('/') and is_valid_path(path[:-1]):
            hostname = req.META.get('HTTP_HOST')
            return HttpResponsePermanentRedirect(
                '%s//%s%s' % (scheme, hostname, path[:-1]))

        return None
