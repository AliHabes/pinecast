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

    def __unicode__(self):
        return '%s: %s' % (self.podcast.slug, self.podcast.name)


class SiteLink(models.Model):
    site = models.ForeignKey(Site)
    title = models.CharField(max_length=256)
    url = models.URLField(blank=True, max_length=500)
    class_name = models.CharField(max_length=256, blank=True, null=True)

class SiteBlogPost(models.Model):
    site = models.ForeignKey(Site)
    title = models.CharField(max_length=512)
    slug = models.SlugField()
    created = models.DateTimeField(auto_now_add=True)
    publish = models.DateTimeField()
    body = models.TextField()

    disable_comments = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s on %s' % (self.slug, self.site.podcast.slug)

    class Meta:
        unique_together = (('site', 'slug'), )
