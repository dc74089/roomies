from itertools import combinations

from app.models import Solution, Request


def suggest_best_connecting_pairs(soln_id):
    s = Solution.objects.get(id=soln_id)

    soln: dict = {room: room.person_ids() for room in s.rooms.all()}

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

    room_pairs.sort(reverse=True, key=lambda x: x[0])

    done = []

    i = 1
    for score, room1, room2 in room_pairs:
        if room1 not in done and room2 not in done:
            room1.highest_affinity_neighbor = room2
            room2.highest_affinity_neighbor = room1

            room1.save()
            room2.save()

            done.append(room1)
            done.append(room2)

            i += 1

        if len(done) + 1 == len(soln):
            pass  # Nothing to do with the last room if count is odd

        if len(done) == len(soln):
            break
