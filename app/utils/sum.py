import json
import random

from django.conf import settings
from django.utils import timezone
from tqdm import tqdm

from app.models import Person, Request, Solution
from app.utils.evaluate import evaluate_solution
from app.utils.hash import hash_solution


db = None


def fill_db():
    global db

    db = {person.id: {p.id: 0 for p in Person.objects.all()} for person in Person.objects.all()}

    for req in Request.objects.filter(type="attract"):
        db[req.requestor.id][req.requestee.id] += 1
        db[req.requestee.id][req.requestor.id] += 1


def helper(eligible, current_room_ids):
    global db

    vals = {i: 0 for i in eligible}
    for person in eligible:
        for room_member_id in current_room_ids:
            vals[person] += db[person.id][room_member_id]

    return sorted(eligible, key=lambda x: vals[x], reverse=True)[0]


def generate_solution(gender):
    out = {}
    placed = []
    next_room = 1

    people = list(Person.objects.filter(gender=gender))
    random.shuffle(people)

    seeds = people[:settings.ROOMS]

    for seed in seeds:
        out[f"Room {next_room}"] = [seed.id]
        placed.append(seed)
        next_room += 1

    while len(placed) < len(people):
        for room in out.keys():
            if len(placed) == len(people): break

            eligible = [i for i in people if i not in placed]
            mvp: Person = helper(eligible, out[room])

            placed.append(mvp)
            out[room].append(mvp.id)

    score, explanation = evaluate_solution(out, gender)

    return score, explanation, out


def generate_solutions(n):
    fill_db()

    for gender in ("Male", "Female"):
        solutions = []
        hashes = []
        best_score = 2**30

        for _ in tqdm(range(n)):
            soln = (generate_solution(gender.lower()))

            if soln[0] < best_score:
                best_score = soln[0]
                solutions = []
                hashes = []
                print(f"\nNew best score: {soln[0]}")

            if soln[0] == best_score and hash_solution(soln[2]) not in hashes:
                solutions.append(soln)
                hashes.append(hash_solution(soln[2]))
                print(f"\nSaving solution with {soln[0]}")

        print(f"Found {len(solutions)} equivalent solutions with score {solutions[0][0]}")

        i = 1
        for x in solutions:
            s = Solution(
                name=f"{gender} rooms generated {timezone.now().strftime('%Y-%m-%d %H:%M')} (#{i})",
                solution=json.dumps(x[2]),
                explanation=x[1]
            )

            s.save()
            i += 1
