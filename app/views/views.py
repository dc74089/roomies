from django.contrib.auth import authenticate, login as do_login, logout as do_logout
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect

from app.models import Person, Solution, SiteConfig


# Create your views here.


def index(request):
    SiteConfig.init_all()

    if request.user.is_authenticated:
        return render(request, "app/admin.html", {
            "solutions": Solution.objects.all(),
            "nonresponses": Person.objects.filter(requests__isnull=True).distinct().order_by('name')
        })
    else:
        if not SiteConfig.objects.get(id="open_for_students"):
            return render(request, 'app/closed.html')

        if 'sid' in request.session:
            return redirect('student_home')

        if "login_error" in request.session:
            error = True
            del request.session['login_error']
            request.session.save()
        else:
            error = False

        return render(request, "app/index.html", {
            "people": Person.objects.all().order_by("name"),
            "error": error
        })


def login(request):
    if request.method == "GET":
        return render(request, 'app/login.html', {'next': request.GET.get('next', "")})
    else:
        data = request.POST
        if 'email' in data and 'password' in data:
            user = authenticate(request, username=data['email'], password=data['password'])

            if user is not None:
                do_login(request, user)
                if data.get('next', ""):
                    return redirect(data['next'])

                return redirect('index')
            else:
                return render(request, 'app/login.html', {
                    'next': data['next'],
                    'error': "Incorrect username or password."
                })

    return HttpResponseBadRequest()


def logout(request):
    do_logout(request)
    request.session.clear()
    request.session.save()
    return redirect('index')
