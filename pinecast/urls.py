from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.i18n import javascript_catalog

import analytics.urls
import dashboard.urls
import feedback.urls
import payments.urls
from . import views
from accounts.urls import urlpatterns as account_urlpatterns
from podcasts.urls import urlpatterns as podcast_urlpatterns


logout_view = lambda r: logout(r) or redirect('home')

js_info_dict = {
    'packages': ('podcasts', 'dashboard'),
}

urlpatterns = (
    account_urlpatterns +
    podcast_urlpatterns +
    [
        url(r'^accounts/login/$', lambda *_: redirect('home')),
        url(r'^admin/', include(admin.site.urls)),
        url(r'^analytics/', include(analytics.urls)),
        url(r'^dashboard/', include(dashboard.urls)),
        url(r'^feedback/', include(feedback.urls)),
        url(r'^logout$', logout_view, name='logout'),
        url(r'^payments/', include(payments.urls)),

        url(r'^services/deploy_complete$', views.deploy_complete),
        url(r'^services/log$', views.log),

        url(r'^jsi18n/$', javascript_catalog, js_info_dict),

        url(r'^favicon\.ico$', lambda *_: redirect('/static/img/favicon.png')),
    ]
)

