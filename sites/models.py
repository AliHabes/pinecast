from __future__ import absolute_import

import json
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy

from accounts.models import UserSettings
from accounts.payment_plans import FEATURE_MIN_SITES, minimum
from podcasts.models import Podcast
from pinecast.helpers import cached_method


GA_VALIDATOR = RegexValidator(r'^[0-9a-zA-Z\-]*$', ugettext_lazy('Only GA IDs are accepted'))

ITUNES_ID_EXTRACTOR = re.compile(r'id(\w+)')

class Site(models.Model):
    SITE_THEMES = (
        # Inspired by http://themepathra.tumblr.com/
        ('panther', ugettext_lazy('Panther')),
        # Inspired by http://demo.themestation.net/podcaster/
        ('podcasty', ugettext_lazy('Podcasty')),
        ('zen', ugettext_lazy('Zen')),
        ('unstyled', ugettext_lazy('Unstyled')),
    )

    podcast = models.OneToOneField(Podcast)
    theme = models.CharField(choices=SITE_THEMES, max_length=16)
    custom_css = models.TextField(blank=True)

    custom_cname = models.CharField(blank=True, null=True, max_length=64)

    cover_image_url = models.URLField(blank=True, null=True, max_length=500)
    favicon_url = models.URLField(blank=True, null=True, max_length=500)
    logo_url = models.URLField(blank=True, null=True, max_length=500)

    itunes_url = models.URLField(blank=True, null=True, max_length=500)
    stitcher_url = models.URLField(blank=True, null=True, max_length=500)

    show_itunes_banner = models.BooleanField(default=False)

    disqus_url = models.CharField(blank=True, null=True, max_length=64)

    analytics_id = models.CharField(blank=True, null=True, max_length=32, validators=[GA_VALIDATOR])

    @cached_method
    def get_domain(self):
        if not self.custom_cname:
            return self.get_subdomain()
        us = UserSettings.get_from_user(self.podcast.owner)
        if not minimum(us.plan, FEATURE_MIN_SITES):
            return self.get_subdomain()

        return 'http://%s' % self.custom_cname

    @cached_method
    def get_subdomain(self):
        return 'http://%s.pinecast.co' % self.podcast.slug

    def get_cover_style(self, bgcolor=None):
        if self.cover_image_url:
            return 'background-image: url(%s)' % self.cover_image_url
        elif bgcolor:
            return 'background-color: %s' % bgcolor
        else:
            return 'background-color: #666'

    def get_banner_id(self):
        if not self.show_itunes_banner:
            return None
        url = self.itunes_url
        if not url:
            return None
        match = ITUNES_ID_EXTRACTOR.search(url)
        if not match:
            return None
        return match.group(1)

    def __str__(self):
        return '%s: %s' % (self.podcast.slug, self.podcast.name)


class SiteLink(models.Model):
    site = models.ForeignKey(Site)
    title = models.CharField(max_length=256)
    url = models.URLField(blank=True, max_length=500)

class SiteBlogPost(models.Model):
    site = models.ForeignKey(Site)
    title = models.CharField(max_length=512)
    slug = models.SlugField()
    created = models.DateTimeField(auto_now_add=True)
    publish = models.DateTimeField()
    body = models.TextField()

    disable_comments = models.BooleanField(default=False)

    def __str__(self):
        return '%s on %s' % (self.slug, self.site.podcast.slug)

    class Meta:
        unique_together = (('site', 'slug'), )


class SitePage(models.Model):
    PAGE_TYPES = (
        ('markdown', ugettext_lazy('Markdown')),
        ('hosts', ugettext_lazy('Hosts')),
        ('contact', ugettext_lazy('Contact')),
    )

    site = models.ForeignKey(Site)
    title = models.CharField(max_length=256)
    slug = models.SlugField()
    page_type = models.CharField(choices=PAGE_TYPES, max_length=16)
    created = models.DateTimeField(auto_now_add=True)

    body = models.TextField()

    @classmethod
    def get_body_from_req(cls, req, page_type=None):
        page_type = page_type or req.POST.get('page_type')
        if page_type == 'markdown':
            return req.POST.get('markdown_body')

        elif page_type == 'hosts':
            blob = []

            try:
                input_blob = json.loads(req.POST.get('host_blob'))
            except Exception:
                input_blob = []

            for host in input_blob:
                if not host.get('name'):
                    continue
                host_blob = {'name': host.get('name')}

                if 'email' in host:
                    host_blob['email'] = str(host.get('email'))[:64]

                if 'twitter' in host:
                    host_blob['twitter'] = str(host.get('twitter'))[:32]
                if 'instagram' in host:
                    host_blob['instagram'] = str(host.get('instagram'))[:32]
                if 'twitch' in host:
                    host_blob['twitch'] = str(host.get('twitch'))[:32]
                if 'youtube' in host:
                    host_blob['youtube'] = str(host.get('youtube'))[:32]
                if 'facebook' in host:
                    host_blob['facebook'] = str(host.get('facebook'))[:256]
                if 'url' in host:
                    host_blob['url'] = str(host.get('url'))[:256]

                blob.append(host_blob)

            return json.dumps(blob)
        elif page_type == 'contact':
            blob = {}

            # I'm saving these all as arrays in case someday we want to allow
            # multiple of each. Easy enough to subscript the array for now, and
            # makes things forward-compatible.

            if req.POST.get('contact_email'):
                blob['email'] = [str(req.POST.get('contact_email', ''))[:64]]
            if req.POST.get('contact_twitter'):
                blob['twitter'] = [str(req.POST.get('contact_twitter', ''))[:32]]
            if req.POST.get('contact_facebook'):
                blob['facebook'] = [str(req.POST.get('contact_facebook', ''))[:256]]
            if req.POST.get('contact_instagram'):
                blob['instagram'] = [str(req.POST.get('contact_instagram', ''))[:32]]
            if req.POST.get('contact_twitch'):
                blob['twitch'] = [str(req.POST.get('contact_twitch', ''))[:32]]
            if req.POST.get('contact_youtube'):
                blob['youtube'] = [str(req.POST.get('contact_youtube', ''))[:32]]
            return json.dumps(blob)
