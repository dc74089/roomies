from app.models import Request, Person, Solution


def evaluate_solution(s: Solution):
    rooms = {
        r.internal_name: r.person_ids() for r in s.rooms.all()
    }

    return evaluate_solution_dict(rooms, s.gender)


def evaluate_solution_dict(soln: dict, gender):
    room_inversion = {}
    running = 0
    total_failures = 0
    total_successes = 0
    complete_failures = []
    stats = {}

    for room in soln:
        for id in soln[room]:
            room_inversion[id] = room

    if gender == "ALL":
        gq = Person.objects.all()
    else:
        gq = Person.objects.filter(gender=gender)

    for person in gq:
        num_reqs = person.requests.filter(manual=False).count()
        num_failures = 0
        num_successes = 0

        if num_reqs == 0: continue

        for req in person.requests.filter(manual=False):
            if req.requestee.id not in room_inversion or req.requestor.id not in room_inversion:
                num_reqs -= 1
                continue

            if req.type == "attract":
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

        try:
            running += (num_failures / num_reqs)
        except ZeroDivisionError:
            pass

        if f"{num_successes} granted requests" not in stats:
            stats[f"{num_successes} granted requests"] = 0

        stats[f"{num_successes} granted requests"] += 1

    for req in Request.objects.filter(manual=True):
        try:
            if req.type == "forbid":
                if room_inversion[req.requestor_id] == room_inversion[req.requestee_id]:
                    running += 1000000
            if req.type == "require":
                if room_inversion[req.requestor_id] != room_inversion[req.requestee_id]:
                    running += 1000000
        except KeyError:
            pass

    line1 = f"{total_failures} failures, {total_successes} successes. Score: {round(running, 3)} \n"
    line2 = f"The following people had zero requests granted: {', '.join(complete_failures)}\n\n" if complete_failures else "Everyone had at least one request granted!\n\n"
    line3 = "\n".join([f"{x}: {stats[x]}" for x in stats])

    return running, (line1 + line2 + line3)
