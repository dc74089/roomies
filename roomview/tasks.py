from app.models import Solution, Person as AppPerson
from roomview.models import Room, Person as RVPerson


def import_solution(soln_id):
    solution = Solution.objects.get(pk=soln_id)

    soln: dict = solution.get_solution()

    for soln_room in soln.keys():
        room = Room(
            name=soln_room
        )

        room.save()

        for sid in soln[soln_room]:
            ap = AppPerson.objects.get(id=sid)
            rvp = RVPerson(
                name=ap.name,
                room=room,
            )

            rvp.save()

        room.save()