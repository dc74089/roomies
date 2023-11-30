from app.models import Request, Person


def evaluate_solution(soln: dict, gender):
    room_inversion = {}
    running = 0
    total_failures = 0
    total_successes = 0
    complete_failures = []

    for room in soln:
        for id in soln[room]:
            room_inversion[id] = room

    for person in Person.objects.filter(gender=gender):
        num_reqs = person.requests.count()
        num_failures = 0

        if num_reqs == 0: continue

        for req in person.requests.all():
            if room_inversion[req.requestor_id] != room_inversion[req.requestee_id]:
                num_failures += 1
                total_failures += 1
            else:
                total_successes += 1

        if num_reqs != 0 and num_reqs == num_failures:
            complete_failures.append(person.name)

        running += (num_failures / num_reqs) ** 4

    return running, (f"{total_failures} failures, {total_successes} successes. \n"
                     f"The following people had zero requests granted: {', '.join(complete_failures)}")


def old_evaluate_solution(soln: dict, gender):
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
        score += failure_inversion[key] * (key ** 4)

    return score, f"{num_failures} failures, {num_successes} successes. {', '.join(out)}"
