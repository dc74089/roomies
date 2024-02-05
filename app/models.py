import hashlib
import json
import math

from django.db import models


class SiteConfig(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    val = models.BooleanField(default=False)
    num = models.IntegerField(default=0)

    def __str__(self):
        return self.id.replace("_", " ").title()

    def __bool__(self):
        return self.val

    def __int__(self):
        return self.num

    @classmethod
    def init_all(cls):
        SiteConfig.objects.get_or_create(id="open_for_students")
        SiteConfig.objects.get_or_create(id="reqs_per_student")
        SiteConfig.objects.get_or_create(id="rooms")
        SiteConfig.objects.get_or_create(id="room_max_capacity")
        SiteConfig.objects.get_or_create(id="students_can_repel")
        SiteConfig.objects.get_or_create(id="site")


# Create your models here.
supported_genders = (
    ("male", "Male"),
    ("female", "Female"),
    ("nb", "Non Binary")
)


class Person(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.TextField()
    gender = models.CharField(max_length=20, choices=supported_genders)

    def __str__(self):
        return f"{self.name} ({self.id})"

    def hashed_id(self):
        return "1" + str(int(self.id) ** 2)[::-1]

    @classmethod
    def unhash_id(cls, id):
        return str(round(math.sqrt(int(str(id)[:0:-1]))))


request_types = (
    ("attract", "requests to be with"),
    ("repel", "requests not to be with"),
    ("forbid", "must not be with"),
    ("require", "must be with")
)


class Request(models.Model):
    requestor = models.ForeignKey('Person', on_delete=models.CASCADE, related_name="requests")
    requestee = models.ForeignKey('Person', on_delete=models.CASCADE, related_name="+")
    type = models.CharField(max_length=20, choices=request_types, default=request_types[0][0])
    manual = models.BooleanField(default=False)

    def __str__(self):
        if self.manual:
            return f"*{self.requestor.name} {self.get_type_display()} {self.requestee.name}*"
        else:
            return f"{self.requestor.name} {self.get_type_display()} {self.requestee.name}"


class Site(models.Model):
    name = models.TextField()
    room_desc = models.TextField(default="{}")
    capacity = models.IntegerField(default=0)

    def set_site(self, site_dict):
        self.room_desc = json.dumps(site_dict)

        self.capacity = sum([int(x['room_capacity']) * int(x['room_count']) for x in site_dict['blocks']])

    def get_site(self):
        return json.loads(self.room_desc)

    def __str__(self):
        return self.name


class Problem(models.Model):
    students = models.ManyToManyField("Person", related_name="problems")
    rooms = models.TextField(null=True, blank=True)


class Solution(models.Model):
    name = models.TextField()
    problem = models.ForeignKey("Problem", on_delete=models.SET_NULL, null=True, blank=True)
    solution = models.TextField()  # Format: uuid as keys, list of person id as vals
    explanation = models.TextField()
    added = models.DateTimeField(auto_now_add=True)
    strategy = models.TextField(null=True, blank=True)

    def set_solution(self, soln_dict):
        self.solution = json.dumps(soln_dict)

    def get_solution(self):
        return json.loads(self.solution)

    def __str__(self):
        return self.name
