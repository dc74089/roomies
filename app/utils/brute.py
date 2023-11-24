import uuid

from app.models import Person, Request


# TODO: UNFINISHED in favor of a smarter algorithm
def generate_solution():
    for _ in range(1000):
        stu_map = {}
        queue = Person.objects.all().order_by("?")

        done = False

        while len(stu_map) != len(queue):
            for student in queue:
                req: Request = student.requests.all().order_by("?").first()

                if student.id not in stu_map:
                    stu_map[student.id] = uuid.uuid4()

                if req.requestee.id not in stu_map:
                    stu_map[req.requestee.id] = stu_map[student.id]
