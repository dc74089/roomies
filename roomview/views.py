from django.http import HttpResponseForbidden
from django.shortcuts import render

from roomview.models import Room

key = "waaolcamr"

# Create your views here.
def activate(request):
    if request.GET.get("key") == key:
        request.session["active"] = True
        request.session.save()

        return render(request, "roomview/activate_success.html")

    return render(request, "roomview/failure.html")


def view_room(request, room_key):
    if not request.session.get("active", False):
        return render(request, "roomview/not_active.html")

    try:
        room = Room.objects.get(key=room_key)
        return render(request, "roomview/single_room.html", {"room": room})

    except Room.DoesNotExist:
        return render(request, "roomview/failure.html")


def all_rooms(request):
    print(request)
    if not request.session.get("active", False):
        return render(request, "roomview/not_active.html")

    return render(request, "roomview/all_rooms.html", {"rooms": Room.objects.all()})


def admin(request):
    if request.user.is_authenticated and request.user.is_staff:
        return render(request, "roomview/admin.html", {"rooms": Room.objects.all()})
    else:
        return HttpResponseForbidden()