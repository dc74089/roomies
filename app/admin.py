from django.contrib import admin

from app.models import *

# Register your models here.
admin.site.register(Person)
admin.site.register(Request)
admin.site.register(Solution)
admin.site.register(SiteConfig)
admin.site.register(Site)