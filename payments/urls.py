from django.conf.urls import url

from . import views
from . import views_tips


urlpatterns = [
    url(r'^tips/(?P<podcast_slug>[\w-]+)$', views.tips, name='tip_jar'),

    url(r'^upgrade$', views.upgrade, name='upgrade'),
    url(r'^upgrade/set_plan$', views.upgrade_set_plan, name='upgrade_set_plan'),

    url(r'^services/set_payment_method$', views.set_payment_method, name='set_payment_method'),
    url(r'^services/set_payment_method_redir$', views.set_payment_method_redir, name='set_payment_method_redir'),
    url(r'^services/set_tip_payment_method$', views_tips.set_tip_payment_method, name='set_tip_payment_method'),
    url(r'^services/send_tip$', views_tips.send_tip, name='send_tip'),
    url(r'^services/set_tip_cashout$', views.set_tip_cashout, name='set_tip_cashout'),
]
