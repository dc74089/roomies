from app.models import Request


def evaluate_solution(soln: dict, gender):
    inverted = {}
    num_successes = 0
    num_failures = 0
    failures_by_person = {}

    for room in soln:
        for person in soln[room]:
            inverted[person] = room

    for request in Request.objects.filter(type='attract', requestor__gender=gender):
        if inverted[request.requestor.id] == inverted[request.requestee.id]:
            num_successes += 1
        else:
            num_failures += 1

            if request.requestor.id not in failures_by_person:
                failures_by_person[request.requestor.id] = 0

            failures_by_person[request.requestor.id] += 1

    failure_inversion = {}
    for person in failures_by_person:
        if failures_by_person[person] not in failure_inversion:
            failure_inversion[failures_by_person[person]] = 0

        failure_inversion[failures_by_person[person]] += 1

    out = []
    score = 0
    for key in sorted(failure_inversion.keys()):
        out.append(f"{failure_inversion[key]} people had {key} failures")
        score += failure_inversion[key] * key * key

    return score, f"{num_failures} failures, {num_successes} successes. {', '.join(out)}"
