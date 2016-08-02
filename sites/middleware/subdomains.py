from django.conf import settings
from django.core.urlresolvers import resolve

from .. import urls_internal
from ..models import Site
from podcasts.models import Podcast


SUBDOMAIN_HOSTS = ['.pinecast.co', '.pinecast.dev']


class SubdomainMiddleware(object):

    def process_request(self, req):
        scheme = 'http' if not req.is_secure() else 'https'
        path = req.get_full_path()
        domain = req.META.get('HTTP_HOST') or req.META.get('SERVER_NAME')

        if settings.DEBUG and ':' in domain:
            domain = domain[:domain.index(':')]

        pieces = domain.split('.')
        if len(pieces) != 3:
            return None

        if domain[len(pieces[0]):] not in SUBDOMAIN_HOSTS:
            return None

        try:
            pod = Podcast.objects.get(slug__iexact=pieces[0])
            site = Site.objects.get(podcast=pod)
        except (Site.DoesNotExist, Podcast.DoesNotExist):
            return None

        path_to_resolve = path if '?' not in path else path[:path.index('?')]
        func, args, kwargs = resolve(path_to_resolve, urls_internal)
        req.META['site_hostname'] = True
        return func(req, podcast_slug=pod.slug, *args, **kwargs)
