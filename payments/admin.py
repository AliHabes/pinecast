from django.contrib import admin

from .models import TipUser, RecurringTip

admin.site.register(TipUser)
admin.site.register(RecurringTip)
