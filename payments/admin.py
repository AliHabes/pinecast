from __future__ import absolute_import

from django.contrib import admin

from .models import RecurringTip, TipEvent, TipUser

admin.site.register(RecurringTip)
admin.site.register(TipEvent)
admin.site.register(TipUser)
