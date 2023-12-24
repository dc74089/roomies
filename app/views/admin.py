import codecs
import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from app.models import Person, request_types, Request, Solution, SiteConfig
from app.utils import evaluate


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


def helper_reqs_granted_in_soln(p_id, room):
    x = 0
    p = Person.objects.get(id=p_id)

    for req in p.requests.all():
        if req.requestee_id in room:
            x += 1

    return x


@login_required
def view_edit_solution(request, id):
    solution = Solution.objects.get(id=id)
    soln = solution.get_solution()

    out = {}

    for room in soln:
        out[room] = []

        for person_id in soln[room]:
            out[room].append((Person.objects.get(id=person_id), helper_reqs_granted_in_soln(person_id, soln[room])))

    return render(request, "app/admin_edit_solution.html", {
        "solution": solution,
        "rooms": out
    })


@login_required
@csrf_exempt
def move_student_in_solution(request):
    print(dict(request.POST))
    if request.user.is_authenticated and request.method == "POST":
        data = request.POST

        if 'solution' in data and 'person' in data and 'to' in data:
            solution = Solution.objects.get(id=data['solution'])
            soln = solution.get_solution()

            for room in soln:
                try:
                    soln[room].remove(data['person'])
                except ValueError:
                    pass

            soln[data['to']].append(data['person'])

            gender = "female" if "female" in solution.name else "male"
            score, explanation = evaluate.evaluate_solution(soln, gender)
            solution.explanation = explanation

            solution.set_solution(soln)
            solution.save()

            counts = {}
            for room in soln:
                for stu in soln[room]:
                    counts[stu] = helper_reqs_granted_in_soln(stu, soln[room])

            return JsonResponse({
                "explanation": explanation.replace("\n", "<br>"),
                "counts": counts
            })

    return HttpResponseBadRequest()


@login_required
def get_stats_for_student(request):
    stu = Person.objects.get(id=request.GET.get("id"))
    solution = Solution.objects.get(id=request.GET.get("solution"))
    soln = solution.get_solution()
    room_inversion = {}
    requests = []
    requested_by = []

    for room in soln:
        for id in soln[room]:
            room_inversion[id] = room

    reqs = stu.requests.all()
    reqd_by = Request.objects.filter(requestee__id=stu.id)

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
