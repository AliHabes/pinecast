from __future__ import absolute_import

from django.contrib import admin

from .models import AssetImportRequest, Collaborator

admin.site.register(AssetImportRequest)
admin.site.register(Collaborator)
