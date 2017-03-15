from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from . import serializers
from podcasts.models import Podcast, PodcastEpisode


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer


class PodcastViewSet(viewsets.ModelViewSet):
    queryset = Podcast.objects.all()
    serializer_class = serializers.PodcastSerializer

    @detail_route(methods=['GET'])
    def episodes(self, req, pk=None):
        episodes = self.get_object().get_episodes()
        ser = serializers.PodcastEpisodeSerializer(episodes, many=True)
        return Response(ser.data)

class PodcastEpisodeViewSet(viewsets.ModelViewSet):
    queryset = PodcastEpisode.objects.all()
    serializer_class = serializers.PodcastEpisodeSerializer
