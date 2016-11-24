from __future__ import absolute_import

from django.conf import settings
from django.core.urlresolvers import resolve
from django.shortcuts import redirect

from .. import urls_internal
from ..models import Site
from accounts.models import UserSettings
from accounts.payment_plans import FEATURE_MIN_CNAME, minimum
from podcasts.models import Podcast


SUBDOMAIN_HOSTS = ['.pinecast.co', '.pinecast.dev']


class NotCNAMEReadyException(Exception):
    pass

class SubdomainMiddleware(object):

    def process_request(self, req):
        scheme = 'http' if not req.is_secure() else 'https'
        domain = req.META.get('HTTP_HOST') or req.META.get('SERVER_NAME')

        if settings.DEBUG and ':' in domain:
            domain = domain[:domain.index(':')]

        pc_forward = req.META.get('HTTP_X_PINECAST_FORWARD')
        if pc_forward:
            try:
                site = Site.objects.get(custom_cname__iexact=pc_forward)
                us = UserSettings.get_from_user(site.podcast.owner)
                if not minimum(us.plan, FEATURE_MIN_CNAME):
                    raise NotCNAMEReadyException()
                return self._resolve(req, site.podcast.slug)
            except (Site.DoesNotExist, NotCNAMEReadyException):
                pass

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

        us = UserSettings.get_from_user(pod.owner)
        if minimum(us.plan, FEATURE_MIN_CNAME) and site.custom_cname:
            return redirect(
                '%s://%s%s' % (scheme, site.custom_cname, req.get_full_path()),
                permanent=True)

        return self._resolve(req, pod.slug)

    def _resolve(self, req, podcast_slug):
        path = req.get_full_path()
        path_to_resolve = path if '?' not in path else path[:path.index('?')]
        func, args, kwargs = resolve(path_to_resolve, urls_internal)
        req.META['site_hostname'] = True
        return func(req, podcast_slug=podcast_slug, *args, **kwargs)
