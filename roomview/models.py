import string

from django.db import models
from django.urls import reverse


# Create your models here.
class Person(models.Model):
    name = models.TextField()
    room = models.ForeignKey("Room", on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'People'

    def __str__(self):
        return self.name


def generate_slug():
    import random

    return "".join([random.choice(string.ascii_letters) for _ in range(6)])


class Room(models.Model):
    key = models.CharField(unique=True, max_length=100, primary_key=True, default=generate_slug)
    name = models.TextField()

    def url(self):
        return "https://roomies.canora.us" + reverse('room', kwargs={"room_key":self.key})

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name
