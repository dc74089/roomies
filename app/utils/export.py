import json

from app.models import Request, supported_genders, Person


def to_json():
    obj = {}

    for gender, _ in supported_genders:
        obj[gender] = [
            {
                "requestor": req.requestor.name,
                "requestee": req.requestee.name
            }

            for req in Request.objects.filter(requestor__gender=gender)
        ]

    return json.dumps(obj)


def to_edgelist():
    out = ""
    for p in Person.objects.all():
        pid = p.id
        reqs = [r.requestee.id for r in p.requests.all()]

        if len(reqs) > 0:
            out += f"{pid} {' '.join(reqs)}\n"

    return out