from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^upgrade$', views.upgrade, name='upgrade'),
    url(r'^upgrade/set_plan$', views.upgrade_set_plan, name='upgrade_set_plan'),
    url(r'^services/set_payment_method$', views.set_payment_method, name='set_payment_method'),
]
