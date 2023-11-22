import codecs
import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from app.models import Person, request_types, Request, Solution


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


def view_edit_solution(request, id):
    solution = Solution.objects.get(id=id)
    soln = solution.get_solution()

    out = {}

    for room in soln:
        out[room] = []
        
        for person_id in soln[room]:
            out[room].append(Person.objects.get(id=person_id))

    return render(request, "app/admin_edit_solution.html", {
        "solution": solution,
        "rooms": out
    })


@csrf_exempt
def move_student_in_solution(request):
    print(dict(request.POST))
    if request.user.is_authenticated and request.method == "POST":
        data = request.POST

        if 'solution' in data and 'person' in data and 'from' in data and 'to' in data:
            solution = Solution.objects.get(id=data['solution'])
            soln = solution.get_solution()

            if data['person'] in soln[data['from']]:
                soln[data['from']].remove(data['person'])
                soln[data['to']].append(data['person'])

            solution.set_solution(soln)
            solution.save()

            return HttpResponse(status=200)

    return HttpResponseBadRequest()
