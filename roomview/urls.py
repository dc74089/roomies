from django.urls import path

from . import views

urlpatterns = [
    path("r/activate", views.activate, name="activate"),

    path('r/admin', views.admin, name='admin'),

    path('r/all', views.all_rooms, name='all_rooms'),

    path('r/<str:room_key>', views.view_room, name='room'),
]