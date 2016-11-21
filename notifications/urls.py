from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^new_notification$', views.new_notification, name='new_notification'),
    url(r'^delete_notification$', views.delete_notification, name='delete_notification'),
]
