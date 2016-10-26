from django.conf.urls import url

from . import views
from . import views_tips


urlpatterns = [
    url(r'^tips/_subscriptions$', views_tips.subscriptions, name='tip_jar_subs'),
    url(r'^tips/_subscriptions/login$', views_tips.subscriptions_login, name='tip_jar_login'),
    url(r'^tips/(?P<podcast_slug>[\w-]+)$', views_tips.tip_flow, name='tip_jar'),
    url(r'^tips/(?P<podcast_slug>[\w-]+)/confirm$', views_tips.confirm_sub, name='tip_jar_confirm_sub'),

    url(r'^upgrade$', views.upgrade, name='upgrade'),
    url(r'^upgrade/set_plan$', views.upgrade_set_plan, name='upgrade_set_plan'),

    url(r'^services/set_payment_method_redir$', views.set_payment_method_redir, name='set_payment_method_redir'),
    url(r'^services/send_tip/(?P<podcast_slug>[\w-]+)$', views_tips.send_tip, name='send_tip'),
    url(r'^services/cancel_sub/(?P<podcast_slug>[\w-]+)$', views_tips.cancel_sub, name='cancel_sub'),
    url(r'^services/set_tip_cashout$', views.set_tip_cashout, name='set_tip_cashout'),
]
