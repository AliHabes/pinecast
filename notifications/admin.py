from __future__ import absolute_import

from django.contrib import admin

from .models import NotificationHook

admin.site.register(NotificationHook)
