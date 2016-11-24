from __future__ import absolute_import

import datetime
import re
import uuid

import gfm
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import URLValidator
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy

import accounts.payment_plans as payment_plans
from accounts.models import Network, UserSettings
from pinecast.helpers import cached_method, reverse, round_now, sanitize


FLAIR_FEEDBACK = 'flair_feedback'
FLAIR_SITE_LINK = 'flair_site_link'
FLAIR_POWERED_BY = 'flair_powered_by'
FLAIR_TIP_JAR = 'flair_tip_jar'
FLAIR_FLAGS = (
    (FLAIR_FEEDBACK, ugettext_lazy('Feedback form link')),
    (FLAIR_SITE_LINK, ugettext_lazy('Link to podcast website')),
    (FLAIR_POWERED_BY, ugettext_lazy('Powered By Pinecast')),
    (FLAIR_TIP_JAR, ugettext_lazy('Tip Jar link')),
)
FLAIR_FLAGS_MAP = {k: v for k, v in FLAIR_FLAGS}


class Podcast(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)

    name = models.CharField(max_length=256)
    subtitle = models.CharField(max_length=512, default='', blank=True)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    cover_image = models.URLField(max_length=500)
    description = models.TextField(blank=True)
    is_explicit = models.BooleanField(default=False)
    homepage = models.URLField(max_length=500, blank=True, validators=[URLValidator()])

    language = models.CharField(max_length=16, default='en-US')
    copyright = models.CharField(max_length=1024, blank=True)
    author_name = models.CharField(max_length=1024, default='Anonymous')

    owner = models.ForeignKey(User)

    rss_redirect = models.URLField(null=True, blank=True, max_length=500)
    stats_base_listens = models.PositiveIntegerField(default=0)

    networks = models.ManyToManyField(Network, blank=True)

    total_tips = models.PositiveIntegerField(
        default=0,
        help_text=ugettext_lazy(
            'Tips collected over podcast lifetime in cents'))

    @cached_method
    def get_site(self):
        try:
            return self.site
        except Exception:
            return None

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
            self.assetimportrequest_set
                .filter(failed=False, resolved=False)
                .count())

    @cached_method
    def get_episodes(self):
        episodes = self.podcastepisode_set.filter(
            publish__lt=round_now(),
            awaiting_import=False).order_by('-publish')
        us = UserSettings.get_from_user(self.owner)
        if us.plan == payment_plans.PLAN_DEMO:
            episodes = episodes[:10]
        return episodes

    @cached_method
    def get_unpublished_count(self):
        return self.podcastepisode_set.filter(
            publish__gt=round_now()).count()

    @cached_method
    def get_most_recent_episode(self):
        episodes = list(self.get_episodes())
        return None if not episodes else episodes[0]

    def get_most_recent_publish_date(self):
        latest = self.get_most_recent_episode()
        return latest.publish if latest else None

    def get_available_flair_flags(self, flatten=False):
        us = UserSettings.get_from_user(self.owner)
        plan = us.plan
        flags = []
        if payment_plans.minimum(plan, payment_plans.PLAN_STARTER):
            # This is inside a conditional because it's forced on for free
            # users.
            flags.append(FLAIR_POWERED_BY)
        if payment_plans.minimum(
                plan, payment_plans.FEATURE_MIN_COMMENT_BOX):
            flags.append(FLAIR_FEEDBACK)
        if us.stripe_payout_managed_account:
            flags.append(FLAIR_TIP_JAR)

        if payment_plans.minimum(
                plan, payment_plans.FEATURE_MIN_SITES) and self.get_site():
            flags.append(FLAIR_SITE_LINK)

        if flatten:
            return flags
        else:
            return [(f, FLAIR_FLAGS_MAP[f]) for f in flags]

    def __unicode__(self):
        return self.name

    def last_eligible_payout_date(self):
        today = datetime.date.today()
        days_since_friday = (today.isoweekday() - 5) % 7
        return today - datetime.timedelta(days=days_since_friday)


    def last_payout_date(self):
        last_eligible_payout_date = self.last_eligible_payout_date()

        last_day_for_charges_in_last_payout = (
            last_eligible_payout_date - datetime.timedelta(days=7))

        last_tip = (self.tip_events
            .filter(occurred_at__lte=last_day_for_charges_in_last_payout)
            .order_by('-occurred_at')
            .first())

        if not last_tip:
            return None

        return last_tip.payout_date()

    def next_payout_date(self):
        last_eligible_payout_date = self.last_eligible_payout_date()
        last_tip = (self.tip_events
                        .filter(occurred_at__gt=last_eligible_payout_date -
                                datetime.timedelta(days=7))
                        .order_by('-occurred_at')
                        .first())

        if not last_tip:
            return None

        return last_tip.payout_date()

    def average_tip_value_this_month(self):
        events = (self.tip_events
            .filter(occurred_at__gt=round_now() - datetime.timedelta(days=30)))
        return events.aggregate(models.aggregates.Avg('amount'))['amount__avg']

    def tip_fees_paid(self):
        return (self.tip_events.all()
                    .aggregate(
                        models.aggregates.Sum('fee_amount')))['fee_amount__sum'] or 0



class PodcastEpisode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(Podcast)
    title = models.CharField(max_length=1024)
    subtitle = models.CharField(max_length=1024, default='', blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    publish = models.DateTimeField()
    description = models.TextField(default='')
    duration = models.PositiveIntegerField(
        help_text=ugettext_lazy('Audio duration in seconds'))

    audio_url = models.URLField(max_length=500)
    audio_size = models.PositiveIntegerField(default=0)
    audio_type = models.CharField(max_length=64)

    image_url = models.URLField(max_length=500)

    copyright = models.CharField(max_length=1024, blank=True)
    license = models.CharField(max_length=1024, blank=True)

    awaiting_import = models.BooleanField(default=False)

    flair_feedback = models.BooleanField(default=False)
    flair_site_link = models.BooleanField(default=False)
    flair_powered_by = models.BooleanField(default=False)
    flair_tip_jar = models.BooleanField(default=False)

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
        return '%02d:%02d:%02d' % (
            seconds // 3600, seconds % 3600 // 60, seconds % 60)

    @cached_method
    def is_published(self):
        return not self.awaiting_import and self.publish <= round_now()


    def set_flair(self, post, no_save=False):
        for flag, _ in FLAIR_FLAGS:
            setattr(self, flag, bool(post.get('flair_%s' % flag)))
        if not no_save:
            self.save()

    def get_html_description(self, is_demo=None):
        raw = self.description
        if is_demo is None:
            us = UserSettings.get_from_user(self.podcast.owner)
            is_demo = us.plan == payment_plans.PLAN_DEMO
        available_flags = self.podcast.get_available_flair_flags(flatten=True)

        if (self.flair_tip_jar and
            FLAIR_TIP_JAR in available_flags):
            raw += '\n\nSupport %s by donating to the [tip jar](https://pinecast.com/payments/tips/%s).' % (
                self.podcast.name, self.podcast.slug)

        if (self.flair_site_link and
            FLAIR_SITE_LINK in available_flags):
            raw += '\n\nFind out more at [%s](http://%s.pinecast.co).' % (
                self.podcast.name, self.podcast.slug)

        if (self.flair_feedback and
            FLAIR_FEEDBACK in available_flags):
            prompt = self.get_feedback_prompt()
            fb_url = 'https://pinecast.com%s' % reverse(
                'ep_comment_box',
                podcast_slug=self.podcast.slug,
                episode_id=str(self.id))
            raw += '\n\n%s [%s](%s)' % (prompt, fb_url, fb_url)

        if (is_demo or
                self.flair_powered_by and
                FLAIR_SITE_LINK in available_flags):
            raw += ('\n\nThis podcast is powered by '
                    '[Pinecast](https://pinecast.com).')

        markdown = gfm.markdown(raw)
        return sanitize(markdown)

    def get_feedback_prompt(self, default=None):
        try:
            prompt = self.episodefeedbackprompt
            return prompt.prompt
        except ObjectDoesNotExist:
            return default if default is not None else ugettext(
                'Send us your feedback online:')

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
