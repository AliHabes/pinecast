from __future__ import absolute_import

from django.contrib import admin

from .models import Podcast, PodcastEpisode, PodcastCategory


class PodcastCategoryInline(admin.TabularInline):
    model = PodcastCategory
    fk_name = 'podcast'
    readonly_fields = ('category', )
    extra = 0

    def get_fields(self, request, obj=None):
        return self.get_readonly_fields(request, obj)

class PodcastEpisodeInline(admin.TabularInline):
    model = PodcastEpisode
    fk_name = 'podcast'
    readonly_fields = ('title', 'publish', 'created', 'duration', )
    extra = 0
    show_change_link = True
    can_delete = False

    def get_fields(self, request, obj=None):
        return self.get_readonly_fields(request, obj)

class PodcastAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'owner_email')
    inlines = (PodcastEpisodeInline, PodcastCategoryInline, )


    # TODO: This is probably not ideal. There's presumably some technical
    # shizzle-wizzle that can be done to prefetch this with, say, the
    # get_queryset method.
    def owner_email(self, obj):
        return obj.owner.email


admin.site.register(Podcast, PodcastAdmin)
admin.site.register(PodcastEpisode)
