from hashlib import md5


def hash_solution(soln: dict):
    out = []

    rooms = sorted([sorted(soln[room]) for room in soln], key=lambda x: sum([int(y) for y in x]))

    for room in rooms:
        out.append(",".join(room))

    return md5("|".join(out).encode('utf-8')).hexdigest()
