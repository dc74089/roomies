from django.urls import path

from .views import views, student, admin

urlpatterns = [
    path('', views.index, name="index"),

    path('home', student.student_home, name="student_home"),
    path('home/createrequest', student.student_create_request, name="student_create_request"),
    path('home/deleterequest', student.student_delete_request, name="student_delete_request"),

    path('login', views.login, name="login"),
    path('logout', views.logout, name="logout"),

    path('admin/csv', admin.csv_import, name="csv"),
    path('admin/togglestudent', admin.toggle_student_availability, name="toggle_student_login"),
    path('admin/createrequest', admin.admin_create_request, name="admin_create_request"),
    path('admin/deleterequest', admin.admin_delete_request, name="admin_delete_request"),

    path('admin/sites/', admin.sites, name="admin_sites"),
    path('admin/sites/edit', admin.edit_site, name="admin_edit_site"),

    path('admin/editsolution/<int:id>', admin.view_edit_solution, name="admin_edit_solution"),
    path('admin/editsolution/movestudent', admin.move_student_in_solution, name="admin_move_student"),
    path('admin/editsolution/getstats', admin.get_stats_for_student, name="admin_get_stats"),
]