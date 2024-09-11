import json
from itertools import combinations

from app.models import Solution, Person, Request


def suggest_best_connecting_pairs(soln_id):
    s = Solution.objects.get(id=soln_id)
    soln: dict = s.get_solution()

    rooms = soln.keys()

    room_pairs = []  # [score, room1, room2]

    for room1, room2 in combinations(rooms, 2):
        room1_kids = soln[room1]  # List of Student IDs
        room2_kids = soln[room2]  # List of Student IDs

        score = 0

        for kid_id in room1_kids:
            reqs = Request.objects.filter(requestor__id=kid_id)

            requested_ids = [req.requestee.id for req in reqs]

            for id in requested_ids:
                if id in room2_kids:
                    score += 1


        room_pairs.append((score, room1, room2))

    room_pairs.sort(reverse=True)

    out = {}
    done = []

    i = 1
    for score, room1, room2 in room_pairs:
        if room1 not in done and room2 not in done:
            out[f"Room {i}A"] = soln[room1]
            out[f"Room {i}B"] = soln[room2]

            done.append(room1)
            done.append(room2)

            i += 1

        if len(done) + 1 == len(soln):
            if room1 not in done:
                out[f"Room {i}"] = soln[room1]
            elif room2 not in done:
                out[f"Room {i}"] = soln[room2]

        if len(done) == len(soln):
            break

    new_soln = Solution(
        name="Paired " + s.name,
        solution=json.dumps(out),
        capacities=s.capacities,
        explanation=s.explanation,
        strategy="Paired " + s.strategy,
        tuned=True
    )

    new_soln.save()
