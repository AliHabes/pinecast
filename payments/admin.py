import uuid

from django.contrib import admin

from .models import RecurringTip, TipEvent, TipUser



def add_id(modeladmin, request, queryset):
    for tu in queryset:
        tu.uuid = str(uuid.uuid4().hex)
        tu.save()
add_id.short_description = 'Add UUID'

class TipUserAdmin(admin.ModelAdmin):
    actions = (add_id, )


admin.site.register(RecurringTip)
admin.site.register(TipEvent)
admin.site.register(TipUser, TipUserAdmin)
