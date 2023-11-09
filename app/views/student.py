from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect

from app.models import Person, Request


def student_home(request):
    if request.method == "POST":
        if 'sid' in request.POST and 'password' in request.POST:
            data = request.POST

            if data['sid'] == data['password']:
                request.session.clear()
                request.session['sid'] = data['sid']
                request.session.save()

                return redirect('student_home')
            else:
                request.session['login_error'] = True
                return redirect('index')
        else:
            return HttpResponseBadRequest()
    else:
        if 'sid' in request.session:
            p = Person.objects.get(id=request.session['sid'])

            reqs = p.requests.all().exclude(manual=True)
            all_requestees = [r.requestee.id for r in reqs]

            eligible_others = Person.objects.filter(gender=p.gender).exclude(id=p.id).exclude(id__in=all_requestees)

            return render(request, "app/student_home.html", {
                "person": p,
                "requests": reqs,
                "others": eligible_others,
                "requests_remaining": settings.REQS_PER_STUDENT - len(reqs)
            })
        else:
            return render()


def student_create_request(request):
    p = Person.objects.get(id=request.session['sid'])

    if request.method == "POST" and 'requestee' in request.POST:
        data = request.POST

        req, created = Request.objects.get_or_create(
            requestor=p,
            requestee_id=data['requestee'],
            manual=False
        )

        req.type = data.get("type", "attract")

        req.save()

        return redirect('student_home')
    else:
        return HttpResponseBadRequest()


def student_delete_request(request):
    p = Person.objects.get(id=request.session['sid'])

    if request.method == "POST" and 'rid' in request.POST:
        data = request.POST

        req = Request.objects.get(id=data['rid'], requestor=p)
        req.delete()

        return redirect('student_home')
    else:
        return HttpResponseBadRequest()
