import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy

from podcasts.models import Podcast


BANNED_SLUGS = set([
    'about',
    'admin',
    'api',
    'apps',
    'asset-cdn',
    'asset-cdn-cf',
    'beta',
    'blog',
    'careers',
    'cdn',
    'chat',
    'community',
    'dmca',
    'download',
    'feed',
    'feedback',
    'feeds',
    'forum',
    'forums',
    'ftp',
    'help',
    'host',
    'jobs',
    'kb',
    'kits',
    'knowledgebase',
    'live',
    'm',
    'mail',
    'media',
    'mobile',
    'next',
    'pop',
    'search',
    'smtp',
    'status',
    'store',
    'support',
    'vpn',
    'webmail',
    'wiki',
    'www',
])

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
    SITE_THEMES_MAP = {k: v for k, v in SITE_THEMES}

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
