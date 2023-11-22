import json

from django.db import models


class SiteConfig(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    val = models.BooleanField(default=False)

    def __str__(self):
        return self.id.replace("_", " ").title()

    def __bool__(self):
        return self.val

    @classmethod
    def init_all(cls):
        SiteConfig.objects.get_or_create(id="open_for_students")


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


class Solution(models.Model):
    name = models.TextField()
    solution = models.TextField()  # Format: uuid as keys, list of person id as vals
    explanation = models.TextField()
    added = models.DateTimeField(auto_now_add=True)

    def set_solution(self, soln_dict):
        self.solution = json.dumps(soln_dict)

    def get_solution(self):
        return json.loads(self.solution)

    def __str__(self):
        return self.name
