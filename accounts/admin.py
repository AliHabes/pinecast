from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Network, UserSettings


class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False
    verbose_name_plural = 'profile'

class UserAdmin(UserAdmin):
    inlines = (UserSettingsInline, )


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(Network)
