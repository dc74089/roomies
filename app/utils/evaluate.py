from app.models import Request, Person


def evaluate_solution(soln: dict, gender):
    room_inversion = {}
    running = 0
    total_failures = 0
    total_successes = 0
    complete_failures = []
    stats = {}

    for room in soln:
        for id in soln[room]:
            room_inversion[id] = room

    for person in Person.objects.filter(gender=gender):
        num_reqs = person.requests.count()
        num_failures = 0
        num_successes = 0

        if num_reqs == 0: continue

        for req in person.requests.all():
            try:
                if room_inversion[req.requestor_id] != room_inversion[req.requestee_id]:
                    num_failures += 1
                    total_failures += 1
                else:
                    num_successes += 1
                    total_successes += 1
            except KeyError:
                num_failures += 1
                total_failures += 1

        if num_reqs != 0 and num_reqs == num_failures:
            complete_failures.append(person.name)
            running += 1000

        running += (num_failures / num_reqs)

        if f"{num_successes}/{person.requests.count()}" not in stats:
            stats[f"{num_successes} granted requests"] = 0

        stats[f"{num_successes} granted requests"] += 1

    line1 = f"{total_failures} failures, {total_successes} successes. Score: {round(running, 3)} \n"
    line2 = f"The following people had zero requests granted: {', '.join(complete_failures)}\n\n" if complete_failures else "Everyone had at least one request granted!\n\n"
    line3 = "\n".join([f"{x}: {stats[x]}" for x in stats])

    return running, (line1 + line2 + line3)


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
