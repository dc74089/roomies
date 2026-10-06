import codecs
import csv
import random

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from app.models import Person, request_types, Request, Solution, SiteConfig, Site, supported_genders, Room


@login_required
def csv_import(request):
    if request.method == "POST" and len(request.FILES) > 0:
        reader = csv.DictReader(codecs.iterdecode(request.FILES['names'], 'utf-8-sig'))

        for row in reader:
            p, created = Person.objects.get_or_create(id=row['ID'])
            p.name = row['Name']
            p.gender = row['Gender']

            p.save()

        return redirect('index')
    else:
        return HttpResponseBadRequest()


@login_required
def admin_create_request(request):
    if request.method == "GET":
        return render(request, "app/admin_create_request.html", {
            "people": Person.objects.all(),
            "request_types": request_types,
            "manual_requests": Request.objects.filter(manual=True)
        })
    else:
        data = request.POST
        if 'requestor' in data and 'requestee' in data and 'type' in data:
            req, created = Request.objects.get_or_create(
                requestor_id=data['requestor'],
                requestee_id=data['requestee'],
                manual=True
            )

            req.type = data['type']
            req.save()

            return redirect('admin_create_request')


@login_required
def admin_delete_request(request):
    if request.method == "POST" and 'rid' in request.POST:
        req = Request.objects.get(id=request.POST['rid'])
        req.delete()

        return redirect('admin_create_request')


@login_required
def toggle_student_availability(request):
    conf = SiteConfig.objects.get(id="open_for_students")
    conf.val = not conf.val
    conf.save()

    return redirect('index')


@login_required
def sites(request):
    if request.method == "POST":
        s = Site(
            name=request.POST['site_name']
        )

        s.save()

        return redirect('admin_sites')
    else:
        sites = Site.objects.all()

        return render(request, "app/admin_sites.html", {"sites": sites})


@login_required
@csrf_exempt
def site_set_active(request):
    if request.method == "POST" and 'id' in request.POST:
        site = Site.objects.get(id=request.POST['id'])

        config = SiteConfig.objects.get(id="site")
        config.num = site.id
        config.save()

        return redirect('admin_sites')
    return HttpResponseBadRequest()


@login_required
@csrf_exempt
def edit_site(request):
    if request.method == "GET":
        if 'id' in request.GET:
            site = Site.objects.get(id=request.GET['id'])
            return render(request, "app/admin_sites_edit.html", {
                "s": site,
                "genders": supported_genders,
                "blocks": site.get_site().get("blocks", [])
            })
        else:
            return HttpResponseBadRequest()
    elif request.method == "POST":
        data = request.POST

        if 'action' in data:
            # ADD BLOCK
            if data['action'] == 'add_block':
                if all([x in data for x in
                        ["id", "block_name", "block_room_count", "block_room_capacity", "block_gender"]]):
                    site = Site.objects.get(id=data['id'])
                    site_dict = site.get_site()

                    if 'blocks' not in site_dict:
                        site_dict['blocks'] = []

                    site_dict['blocks'].append({
                        "name": data['block_name'],
                        "room_count": data['block_room_count'],
                        "room_capacity": data['block_room_capacity'],
                        "gender": data['block_gender'],
                        "description": f"{data['block_room_count']} {data['block_gender']} rooms each sleeping {data['block_room_capacity']}"
                    })

                    site.set_site(site_dict)
                    site.save()

                    return HttpResponse(status=200)
            if data['action'] == "del_block":
                if all([x in data for x in ["id", "block_idx"]]):
                    site = Site.objects.get(id=data['id'])
                    site_dict = site.get_site()

                    site_dict['blocks'].pop(int(data['block_idx']))

                    site.set_site(site_dict)
                    site.save()

                    return HttpResponse(status=200)


@login_required
def graph_vis(request):
    show_names = request.GET.get("names", 1) == 1

    return render(request, 'app/admin_visualize_requests.html', {
        "data": {
            "nodes": [{
                "key": p.id,
                "attributes": {
                    "label": p.name if show_names else None,
                    "gender": p.gender,
                    "x": random.randint(-100, 100),
                    "y": random.randint(-100, 100),
                }
            } for p in Person.objects.all()],
            "edges": [{
                "source": r.requestor.id,
                "target": r.requestee.id
            } for r in Request.objects.filter(type="attract", manual=False)]
        }
    })


@login_required
def view_edit_solution(request, id):
    solution = get_object_or_404(Solution, id=id)
    rooms = solution.rooms.prefetch_related('people').order_by('internal_name')

    placed_ids = {p.id for room in rooms for p in room.people.all()}
    people = Person.objects.filter(Q(gender=solution.gender) | Q(id__in=placed_ids)).order_by('name')
    people_ids = {p.id for p in people}

    payload = {
        "solution": {
            "id": solution.id,
            "name": solution.name,
            "strategy": solution.strategy,
            "gender": solution.gender,
            "score": solution.score,
        },
        "rooms": [{
            "id": room.id,
            "internal_name": room.internal_name,
            "placed_name": room.placed_name or "",
            "capacity": room.capacity,
            "people": [p.id for p in room.people.all()],
        } for room in rooms],
        "unplaced": [p.id for p in people if p.id not in placed_ids],
        "people": [{"id": p.id, "name": p.name, "gender": p.gender} for p in people],
        "requests": [{
            "requestor": r.requestor_id,
            "requestee": r.requestee_id,
            "type": r.type,
            "manual": r.manual,
        } for r in Request.objects.filter(requestor_id__in=people_ids, requestee_id__in=people_ids)],
    }

    return render(request, 'app/admin_solution_edit_new.html', {
        "solution": solution,
        "payload": payload,
    })


@login_required
def move_student_in_solution(request):
    data = request.POST

    if request.method != "POST" or not all(k in data for k in ('solution', 'person', 'to')):
        return HttpResponseBadRequest()

    soln = get_object_or_404(Solution, id=data['solution'])
    student = get_object_or_404(Person, id=data['person'])

    with transaction.atomic():
        for room in soln.rooms.filter(people=student):
            room.people.remove(student)

        # An empty "to" leaves the student unplaced
        if data['to']:
            get_object_or_404(soln.rooms, id=data['to']).people.add(student)

    return JsonResponse({"ok": True})


@login_required
def swap_students_in_solution(request):
    data = request.POST

    if request.method != "POST" or not all(k in data for k in ('solution', 'a', 'b')):
        return HttpResponseBadRequest()

    soln = get_object_or_404(Solution, id=data['solution'])
    a = get_object_or_404(Person, id=data['a'])
    b = get_object_or_404(Person, id=data['b'])

    with transaction.atomic():
        room_a = soln.rooms.filter(people=a).first()
        room_b = soln.rooms.filter(people=b).first()

        if room_a is None or room_b is None or room_a == room_b:
            return HttpResponseBadRequest()

        room_a.people.remove(a)
        room_b.people.remove(b)
        room_a.people.add(b)
        room_b.people.add(a)

    return JsonResponse({"ok": True})


@login_required
def reevaluate_solution(request):
    solution = get_object_or_404(Solution, id=request.GET.get("solution"))
    solution.reevaluate_score()

    return JsonResponse({
        "score": solution.score,
        "explanation": solution.explanation.replace("\n", "<br>"),
    })


@login_required
def rename_room_in_solution(request):
    data = request.POST

    if request.method != "POST" or 'id' not in data or 'new' not in data:
        return HttpResponseBadRequest()

    room = get_object_or_404(Room, id=data['id'])
    room.placed_name = data['new'].strip()
    room.save()

    return JsonResponse({"ok": True, "placed_name": room.placed_name})


@login_required
def get_stats_for_student(request):
    stu = Person.objects.get(id=request.GET.get("id"))
    solution = Solution.objects.get(id=request.GET.get("solution"))
    room_inversion = {}
    requests = []
    requested_by = []

    for room in solution.rooms.all():
        for id in room.person_ids():
            room_inversion[id] = room

    reqs = stu.requests.filter(manual=False)
    reqd_by = Request.objects.filter(requestee__id=stu.id, manual=False)

    for req in reqs:
        requests.append({
            "name": req.requestee.name,
            "satisfied": "✅" if room_inversion[req.requestor_id] == room_inversion[req.requestee_id] else "❌"
        })

    for req in reqd_by:
        requested_by.append({
            "name": req.requestor.name,
            "satisfied": "✅" if room_inversion[req.requestor_id] == room_inversion[req.requestee_id] else "❌"
        })

    return JsonResponse({
        "name": stu.name,
        "requests": requests,
        "requested_by": requested_by
    })


@login_required
def get_simplified_stats(request):
    stu = Person.objects.get(id=request.GET.get("id"))
    room_inversion = {}
    requests = []
    requested_by = []

    reqs = stu.requests.all()
    reqd_by = Request.objects.filter(requestee__id=stu.id, manual=False)

    for req in reqs:
        requests.append({
            "name": req.requestee.name,
        })

    for req in reqd_by:
        requested_by.append({
            "name": req.requestor.name,
        })

    return JsonResponse({
        "name": stu.name,
        "requests": requests,
        "requested_by": requested_by
    })
