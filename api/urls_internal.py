from django.conf import settings
from django.conf.urls import include, url
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'podcasts', views.PodcastViewSet)
router.register(r'episodes', views.PodcastEpisodeViewSet)

print(router.urls)
urlpatterns = [
    url(r'^v1/', include(router.urls)),
    url(r'^v1/api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]

