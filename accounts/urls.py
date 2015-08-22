from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^login$', views.login_page, name='login'),
    url(r'^beta_signup$', views.private_beta_signup, name='beta_signup'),

    url(r'^accounts/settings$', views.user_settings_page, name='user_settings'),
    url(r'^accounts/settings/save_timezone$', views.user_settings_page_savetz, name='user_settings_save_tz'),
    url(r'^accounts/settings/change_username$', views.user_settings_page_changeusername, name='user_settings_change_username'),
    url(r'^accounts/settings/change_password$', views.user_settings_page_changepassword, name='user_settings_change_password'),
    url(r'^accounts/settings/change_email$', views.user_settings_page_changeemail, name='user_settings_change_email'),
    url(r'^accounts/settings/change_email/finalize$', views.user_settings_page_changeemail_finalize, name='user_settings_change_email_finalize'),
]
