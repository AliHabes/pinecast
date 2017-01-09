from __future__ import absolute_import

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Network, UserSettings
from podcasts.models import Podcast


class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False
    verbose_name_plural = 'profile'


class PodcastInline(admin.TabularInline):
    model = Podcast
    fk_name = 'owner'
    readonly_fields = ('slug', 'name', )
    extra = 0
    show_change_link = True
    can_delete = False

    def get_fields(self, request, obj=None):
        return self.get_readonly_fields(request, obj)

class UserAdmin(UserAdmin):
    inlines = (UserSettingsInline, PodcastInline)
    list_display = ('email', 'username', )


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(Network)
