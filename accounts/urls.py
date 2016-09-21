from django.conf.urls import url

from . import views
from . import views_signup


urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^login$', views.login_page, name='login'),
    url(r'^forgot_password$', views.forgot_password, name='forgot_password'),
    url(r'^forgot_password/finalize$', views.forgot_password_finalize, name='forgot_password_finalize'),
    url(r'^forgot_password/finish$', views.forgot_password_finish, name='forgot_password_finish'),

    url(r'^accounts/settings$', views.user_settings_page, name='user_settings'),
    url(r'^accounts/settings/save_timezone$', views.user_settings_page_savetz, name='user_settings_save_tz'),
    url(r'^accounts/settings/change_password$', views.user_settings_page_changepassword, name='user_settings_change_password'),
    url(r'^accounts/settings/change_email$', views.user_settings_page_changeemail, name='user_settings_change_email'),
    url(r'^accounts/settings/change_email/finalize$', views.user_settings_page_changeemail_finalize, name='user_settings_change_email_finalize'),

    url(r'^signup$', views_signup.signup, name='signup'),
]
