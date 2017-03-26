from __future__ import absolute_import

from django.conf import settings
from django.core.urlresolvers import resolve
from django.shortcuts import redirect

from .. import urls_internal
from .. import urls_pinecast_co
from ..models import Site
from accounts.models import UserSettings
from accounts.payment_plans import FEATURE_MIN_CNAME, FEATURE_MIN_SITES, minimum
from podcasts.models import Podcast


RAW_SUBDOMAIN_HOSTS = ['pinecast.co', 'pinecast.dev']
SUBDOMAIN_HOSTS = ['.pinecast.co', '.pinecast.dev']


class NotCNAMEReadyException(Exception):
    pass

class SubdomainMiddleware(object):

    def process_request(self, req):
        scheme = 'http' if not req.is_secure() else 'https'
        domain = req.META.get('HTTP_HOST') or req.META.get('SERVER_NAME')

        if settings.DEBUG and ':' in domain:
            domain = domain[:domain.index(':')]

        if domain in RAW_SUBDOMAIN_HOSTS:
            path = req.get_full_path()
            func, args, kwargs = resolve(path, urls_pinecast_co)
            return func(req, *args, **kwargs)

        pc_forward = req.META.get('HTTP_X_PINECAST_FORWARD')
        if pc_forward and pc_forward.endswith('.pinecast.co'):
            domain = pc_forward
        elif pc_forward:
            try:
                site = Site.objects.get(custom_cname__iexact=pc_forward)

                if FEATURE_MIN_SITES != FEATURE_MIN_CNAME:
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

        can_have_cname = (
            True if FEATURE_MIN_CNAME == FEATURE_MIN_SITES else
            minimum(UserSettings.get_from_user(pod.owner).plan, FEATURE_MIN_CNAME))
        if can_have_cname and site.custom_cname:
            return redirect(
                '%s://%s%s' % (scheme, site.custom_cname, req.get_full_path()),
                permanent=True)

        return self._resolve(req, pod.slug)

    def _resolve(self, req, podcast_slug):
        path = req.get_full_path()
        path_to_resolve = path if '?' not in path else path[:path.index('?')]
        func, args, kwargs = resolve(path_to_resolve, urls_internal)
        if settings.DEBUG_TOOLBAR and path.startswith('/__debug__/'):
            return func(req, *args, **kwargs)
        req.META['site_hostname'] = True
        return func(req, podcast_slug=podcast_slug, *args, **kwargs)
