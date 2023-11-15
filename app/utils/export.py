import json

from app.models import Request, supported_genders


def export():
    obj = {}

    for gender, _ in supported_genders:
        obj[gender] = [
            {
                "requestor": req.requestor,
                "requestee": req.requestee
            }

            for req in Request.objects.filter(requestor__gender=gender)
        ]

    return json.dumps(obj)
