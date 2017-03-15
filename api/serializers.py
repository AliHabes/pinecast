from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import UserSettings
from podcasts.models import Podcast, PodcastEpisode, PodcastCategory


class UserSettingsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UserSettings
        fields = ('id', 'plan', 'tz_offset', 'coupon_code', )
        ready_only_fields = ('plan', 'coupon_code', )


class UserSerializer(serializers.HyperlinkedModelSerializer):
    usersettings = UserSettingsSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'usersettings', )
        ready_only_fields = fields


class PodcastCategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PodcastCategory
        fields = ('category', )
        ready_only_fields = fields

    def to_representation(self, obj):
        return obj.category


class PodcastSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='user-detail')
    episodes = serializers.HyperlinkedIdentityField(read_only=True, view_name='podcast-episodes')
    categories = PodcastCategorySerializer(read_only=True, many=True, source='podcastcategory_set')

    class Meta:
        model = Podcast
        fields = ('id', 'slug', 'name', 'subtitle', 'created', 'cover_image',
                  'description', 'is_explicit', 'homepage', 'language',
                  'copyright', 'author_name', 'owner', 'rss_redirect',
                  'total_tips', 'private_after_nth', 'private_after_age',
                  'private_access_min_subscription', 'episodes', 'categories')
        ready_only_fields = fields

class PodcastEpisodeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PodcastEpisode
        fields = ('id', 'title', 'subtitle', 'created', 'publish', 'description',
                  'duration', 'audio_url', 'audio_size', 'audio_type',
                  'image_url', 'copyright', 'license', 'awaiting_import',
                  'flair_feedback', 'flair_site_link', 'flair_tip_jar',
                  'flair_referral_code', 'explicit_override', 'is_private', )
        ready_only_fields = fields
