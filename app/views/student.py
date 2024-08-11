from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect

from app.models import Person, Request, SiteConfig


def student_home(request):
    if not SiteConfig.objects.get(id="open_for_students"):
        return redirect('logout')

    if request.method == "POST":
        if 'sid' in request.POST and 'password' in request.POST:
            data = request.POST
            sid = Person.unhash_id(data['sid'])

            if sid == data['password']:
                request.session.clear()
                request.session['sid'] = sid
                request.session.save()

                return redirect('student_home')
            else:
                request.session['login_error'] = True
                return redirect('index')
        else:
            return HttpResponseBadRequest()
    else:
        if 'sid' in request.session:
            try:
                p = Person.objects.get(id=request.session['sid'])
            except Person.DoesNotExist:
                return redirect('logout')

            reqs = p.requests.all().exclude(manual=True)
            all_requestees = [r.requestee.id for r in reqs]

            eligible_others = (
                Person.objects
                .filter(gender=p.gender)
                .exclude(id=p.id)
                .exclude(id__in=all_requestees)
                .order_by('name')
            )

            return render(request, "app/student_home.html", {
                "person": p,
                "requests": reqs,
                "others": eligible_others,
                "requests_remaining": SiteConfig.objects.get(id="reqs_per_student").num - len(reqs)
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
