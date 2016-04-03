import datetime
import re
import uuid

import gfm
import requests
from bitfield import BitField
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy

import accounts.payment_plans as payment_plans
from accounts.models import Network, UserSettings
from pinecast.helpers import cached_method, reverse, sanitize


FLAIR_FEEDBACK = 'feedback_link'
FLAIR_SITE_LINK = 'site_link'
FLAIR_POWERED_BY = 'powered_by'
FLAIR_FLAGS = (
    (FLAIR_FEEDBACK, ugettext_lazy('Feedback Link')),
    (FLAIR_SITE_LINK, ugettext_lazy('Site Link')),
    (FLAIR_POWERED_BY, ugettext_lazy('Powered By Pinecast')),
)
FLAIR_FLAGS_MAP = {k: v for k, v in FLAIR_FLAGS}


class Podcast(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)

    name = models.CharField(max_length=256)
    subtitle = models.CharField(max_length=512, default='', blank=True)

    created = models.DateTimeField(auto_now=True)
    cover_image = models.URLField()
    description = models.TextField()
    is_explicit = models.BooleanField()
    homepage = models.URLField()

    language = models.CharField(max_length=16)
    copyright = models.CharField(max_length=1024, blank=True)
    author_name = models.CharField(max_length=1024)

    owner = models.ForeignKey(User)

    rss_redirect = models.URLField(null=True, blank=True)
    stats_base_listens = models.PositiveIntegerField(default=0)

    networks = models.ManyToManyField(Network)

    total_tips = models.PositiveIntegerField(
        default=0,
        help_text=ugettext_lazy('Tips collected over podcast lifetime in cents'))
    tip_value = models.PositiveIntegerField(
        default=0,
        help_text=ugettext_lazy('Unpaid tip value in cents'))
    tip_last_payout = models.DateTimeField(default=None, null=True)
    tip_last_payout_amount = models.PositiveIntegerField(
        default=0,
        help_text=ugettext_lazy('Last tip payout value paid out in cents'))


    @cached_method
    def get_category_list(self):
        return ','.join(x.category for x in self.podcastcategory_set.all())

    def set_category_list(self, cat_str):
        existing = set(x.category for x in self.podcastcategory_set.all())
        new = set(cat_str.split(','))

        added = new - existing
        removed = existing - new

        for a in added:
            n = PodcastCategory(podcast=self, category=a)
            n.save()

        for r in removed:
            o = PodcastCategory.objects.get(podcast=self, category=r)
            o.delete()

    @cached_method
    def is_still_importing(self):
        return bool(
            self.assetimportrequest_set.filter(failed=False, resolved=False).count())

    @cached_method
    def get_episodes(self):
        episodes = self.podcastepisode_set.filter(
            publish__lt=datetime.datetime.now(),
            awaiting_import=False).order_by('-publish')
        if UserSettings.get_from_user(self.owner).plan == payment_plans.PLAN_DEMO:
            episodes = episodes[:10]
        return episodes

    @cached_method
    def get_unpublished_count(self):
        return self.podcastepisode_set.filter(publish__gt=datetime.datetime.now()).count()

    @cached_method
    def get_most_recent_episode(self):
        if not self.get_episodes().count():
            return None
        return self.get_episodes()[0]

    def get_most_recent_publish_date(self):
        latest = self.get_most_recent_episode()
        return latest.publish if latest else None

    def get_available_flair_flags(self, flatten=False):
        plan = UserSettings.get_from_user(self.owner).plan
        flags = []
        if payment_plans.minimum(plan, payment_plans.PLAN_STARTER):
            # This is inside a conditional because it's forced on for free
            # users.
            flags.append(FLAIR_POWERED_BY)
        if payment_plans.minimum(plan, payment_plans.FEATURE_MIN_COMMENT_BOX):
            flags.append(FLAIR_FEEDBACK)
        try:
            if payment_plans.minimum(plan, payment_plans.FEATURE_MIN_SITES) and self.site:
                flags.append(FLAIR_SITE_LINK)
        except Exception:
            # FIXME: Catch the correct exception here.
            # `RelatedObjectDoesNotExist` is a strange and fickle beast.
            pass

        if flatten:
            return flags
        else:
            return [(f, FLAIR_FLAGS_MAP[f]) for f in flags]

    def __unicode__(self):
        return self.name


class PodcastEpisode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(Podcast)
    title = models.CharField(max_length=1024)
    subtitle = models.CharField(max_length=1024, default='', blank=True)
    created = models.DateTimeField(auto_now=True)
    publish = models.DateTimeField()
    description = models.TextField(default='')
    duration = models.PositiveIntegerField(help_text=ugettext_lazy('Audio duration in seconds'))

    audio_url = models.URLField()
    audio_size = models.PositiveIntegerField(default=0)
    audio_type = models.CharField(max_length=64)

    image_url = models.URLField()

    copyright = models.CharField(max_length=1024, blank=True)
    license = models.CharField(max_length=1024, blank=True)

    awaiting_import = models.BooleanField(default=False)

    description_flair = BitField(
        flags=FLAIR_FLAGS,
        default=0
    )

    EXPLICIT_OVERRIDE_CHOICE_NONE = 'none'
    EXPLICIT_OVERRIDE_CHOICE_EXPLICIT = 'expl'
    EXPLICIT_OVERRIDE_CHOICE_CLEAN = 'clen'
    explicit_override = models.CharField(
        max_length=4,
        choices=[
            (EXPLICIT_OVERRIDE_CHOICE_NONE, ugettext_lazy('None')),
            (EXPLICIT_OVERRIDE_CHOICE_EXPLICIT, ugettext_lazy('Explicit')),
            (EXPLICIT_OVERRIDE_CHOICE_CLEAN, ugettext_lazy('Clean')),
        ],
        default=EXPLICIT_OVERRIDE_CHOICE_NONE
    )

    @cached_method
    def formatted_duration(self):
        seconds = self.duration
        return '%02d:%02d:%02d' % (seconds // 3600, seconds % 3600 // 60, seconds % 60)

    @cached_method
    def is_published(self):
        return not self.awaiting_import and self.publish <= datetime.datetime.now()


    def set_flair(self, post, no_save=False):
        val = 0
        for flag, _ in FLAIR_FLAGS:
            if post.get('flair_%s' % flag):
                val = val | getattr(PodcastEpisode.description_flair, flag)
        self.description_flair = val
        if not no_save:
            self.save()

    def get_html_description(self, is_demo=None):
        raw = self.description
        if is_demo is None:
            is_demo = UserSettings.get_from_user(self.podcast.owner).plan == payment_plans.PLAN_DEMO
        available_flags = self.podcast.get_available_flair_flags(flatten=True)

        if (self.description_flair.site_link and
            FLAIR_SITE_LINK in available_flags):
            raw += '\n\nFind out more at [%s](http://%s.pinecast.co).' % (
                self.podcast.name, self.podcast.slug)

        if (self.description_flair.feedback_link and
            FLAIR_FEEDBACK in available_flags):
            prompt = self.get_feedback_prompt()
            fb_url = 'https://pinecast.com%s' % reverse(
                'ep_comment_box', podcast_slug=self.podcast.slug, episode_id=str(self.id))
            raw += '\n\n%s [%s](%s)' % (prompt, fb_url, fb_url)

        if (is_demo or
            self.description_flair.powered_by and FLAIR_SITE_LINK in available_flags):
            raw += '\n\nThis podcast is powered by [Pinecast](https://pinecast.com).'

        markdown = gfm.markdown(raw)
        return sanitize(markdown)

    def get_feedback_prompt(self, default=None):
        try:
            prompt = self.episodefeedbackprompt
            return prompt.prompt
        except ObjectDoesNotExist:
            return default if default is not None else ugettext('Send us your feedback online:')

    def delete_feedback_prompt(self):
        try:
            self.episodefeedbackprompt.delete()
        except ObjectDoesNotExist:
            pass

    def __unicode__(self):
        return '%s - %s' % (self.title, self.subtitle)


CATEGORIES = set([
    'Arts',
    'Arts/Design',
    'Arts/Fashion & Beauty',
    'Arts/Food',
    'Arts/Literature',
    'Arts/Performing Arts',
    'Arts/Spoken Word',
    'Arts/Visual Arts',
    'Business',
    'Business/Business News',
    'Business/Careers',
    'Business/Investing',
    'Business/Management & Marketing',
    'Business/Shopping',
    'Comedy',
    'Education',
    'Education/Educational Technology',
    'Education/Higher Education',
    'Education/K-12',
    'Education/Language Courses',
    'Education/Training',
    'Games & Hobbies',
    'Games & Hobbies/Automotive',
    'Games & Hobbies/Aviation',
    'Games & Hobbies/Hobbies',
    'Games & Hobbies/Other Games',
    'Games & Hobbies/Video Games',
    'Government & Organizations',
    'Government & Organizations/Local',
    'Government & Organizations/National',
    'Government & Organizations/Non-Profit',
    'Government & Organizations/Regional',
    'Health',
    'Health/Alternative Health',
    'Health/Fitness & Nutrition',
    'Health/Self-Help',
    'Health/Sexuality',
    'Health/Kids & Family',
    'Music',
    'Music/Alternative',
    'Music/Blues',
    'Music/Country',
    'Music/Easy Listening',
    'Music/Electronic',
    'Music/Electronic/Acid House',
    'Music/Electronic/Ambient',
    'Music/Electronic/Big Beat',
    'Music/Electronic/Breakbeat',
    'Music/Electronic/Disco',
    'Music/Electronic/Downtempo',
    'Music/Electronic/Drum \'n\' Bass',
    'Music/Electronic/Garage',
    'Music/Electronic/Hard House',
    'Music/Electronic/House',
    'Music/Electronic/IDM',
    'Music/Electronic/Jungle',
    'Music/Electronic/Progressive',
    'Music/Electronic/Techno',
    'Music/Electronic/Trance',
    'Music/Electronic/Tribal',
    'Music/Electronic/Trip Hop',
    'Music/Folk',
    'Music/Freeform',
    'Music/Hip-Hop & Rap',
    'Music/Inspirational',
    'Music/Jazz',
    'Music/Latin',
    'Music/Metal',
    'Music/New Age',
    'Music/Oldies',
    'Music/Pop',
    'Music/R&B & Urban',
    'Music/Reggae',
    'Music/Rock',
    'Music/Seasonal & Holiday',
    'Music/Soundtracks',
    'Music/World',
    'News & Politics',
    'News & Politics/Conservative (Right)',
    'News & Politics/Liberal (Left)',
    'Religion & Spirituality',
    'Religion & Spirituality/Buddhism',
    'Religion & Spirituality/Christianity',
    'Religion & Spirituality/Hinduism',
    'Religion & Spirituality/Islam',
    'Religion & Spirituality/Judaism',
    'Religion & Spirituality/Other',
    'Religion & Spirituality/Spirituality',
    'Science & Medicine',
    'Science & Medicine/Medicine',
    'Science & Medicine/Natural Sciences',
    'Science & Medicine/Social Sciences',
    'Society & Culture',
    'Society & Culture/Gay & Lesbian',
    'Society & Culture/History',
    'Society & Culture/Personal Journals',
    'Society & Culture/Philosophy',
    'Society & Culture/Places & Travel',
    'Sports & Recreation',
    'Sports & Recreation/Amateur',
    'Sports & Recreation/College & High School',
    'Sports & Recreation/Outdoor',
    'Sports & Recreation/Professional',
    'TV & Film',
    'Technology',
    'Technology/Gadgets',
    'Technology/IT News',
    'Technology/Podcasting',
    'Technology/Software How-To',
])

class PodcastCategory(models.Model):
    category = models.CharField(max_length=128,
                                choices=[(x, x) for x in CATEGORIES])
    podcast = models.ForeignKey(Podcast)

    def __unicode__(self):
        return '%s: %s' % (self.podcast.name, self.category)


class PodcastReviewAssociation(models.Model):
    SERVICE_ITUNES = 'ITUNES'
    SERVICE_STITCHER = 'STITCHER'
    SERVICES = (
        (SERVICE_ITUNES, 'iTunes'),
        (SERVICE_STITCHER, 'Stitcher Radio'),
    )
    SERVICES_SET = set(x for x, y in SERVICES)
    SERVICES_MAP = {x: y for x, y in SERVICES}

    EXAMPLE_URLS = {
        SERVICE_ITUNES: 'https://itunes.apple.com/us/podcast/this-american-life/id201671138',
        SERVICE_STITCHER: 'http://www.stitcher.com/podcast/this-american-life',
    }

    podcast = models.ForeignKey(Podcast)  # Not one-to-one because you can have multiple services
    service = models.CharField(choices=SERVICES, max_length=16)
    payload = models.CharField(max_length=256)

    def __unicode__(self):
        return '%s: %s' % (self.podcast.name, self.service)

    @classmethod
    def create_for_service(cls, service, **kwargs):
        kwargs['service'] = service
        if service == SERVICE_STITCHER:
            return cls.create_service_stitcher(**kwargs)
        elif service == SERVICE_ITUNES:
            return cls.create_service_itunes(**kwargs)
        else:
            raise Exception('Unknown service')

    @classmethod
    def create_service_stitcher(cls, **kwargs):
        stitcher_page = requests.get(kwargs['url'], timeout=5)
        result = re.search(r'productId:\s+"(\w+)"', stitcher_page.text)
        if not result:
            raise Exception(ugettext('Could not find podcast ID'))

        return cls(payload=result.group(1), **kwargs)

    @classmethod
    def create_service_itunes(cls, **kwargs):
        page = requests.get(kwargs['url'], timeout=5, headers={'user-agent': 'iTunes/9.1.1'})
        result = re.search(r'<string>\s*(https://itunes\.apple\.com/.*)\s*</string>', page.text)
        if not result:
            raise Exception(ugettext('Could not find podcast ID'))

        return cls(payload=result.group(1), **kwargs)
