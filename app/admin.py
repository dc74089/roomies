from django.contrib import admin

from app.models import *


class NameSortAdmin(admin.ModelAdmin):
    ordering = ('name',)


# Register your models here.
admin.site.register(Person, NameSortAdmin)
admin.site.register(Request)
admin.site.register(Solution)
admin.site.register(SiteConfig)
admin.site.register(Site)
admin.site.register(Room)
