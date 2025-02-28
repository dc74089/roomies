from django.contrib import admin

from roomview.models import Room, Person

# Register your models here.
admin.site.register(Person)
admin.site.register(Room)