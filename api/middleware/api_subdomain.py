import rest_framework.reverse
from django.conf import settings
from django.core.urlresolvers import resolve
from django.shortcuts import redirect

from .. import urls_internal


API_HOSTS = ['api.pinecast.com', 'api.pinecast.dev']

orig_drf_reverse = rest_framework.reverse._reverse
rest_framework.reverse._reverse = lambda *args, **kw: orig_drf_reverse(*args, urlconf=urls_internal, **kw)


class APISubdomainMiddleware(object):

    def process_request(self, req):
        domain = req.META.get('HTTP_HOST') or req.META.get('SERVER_NAME')
        if ':' in domain:
            domain = domain[:domain.index(':')]

        if domain not in API_HOSTS:
            return None

        path = req.get_full_path()
        path_to_resolve = path if '?' not in path else path[:path.index('?')]
        func, args, kwargs = resolve(path_to_resolve, urls_internal)
        return func(req, *args, **kwargs)
