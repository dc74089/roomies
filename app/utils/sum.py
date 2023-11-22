import json
import random
import uuid

from django.conf import settings
from django.utils import timezone
from tqdm import tqdm

from app.models import Person, Request, Solution
from app.utils.evaluate import evaluate_solution


def helper(eligible, current_room_ids):
    vals = {i: 0 for i in eligible}
    for person in eligible:
        vals[person] += Request.objects.filter(requestor__id__in=current_room_ids, requestee=person).count()
        vals[person] += Request.objects.filter(requestee__id__in=current_room_ids, requestor=person).count()

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
    for gender in ("Male", "Female"):
        solutions = []
        best_score = 2**30

        for _ in tqdm(range(n)):
            soln = (generate_solution(gender.lower()))

            if soln[0] < best_score:
                best_score = soln[0]
                solutions = []

            if soln[0] == best_score:
                solutions.append(soln)

        print(f"Found {len(solutions)} equivalent solutions with score {soln[0]}")

        i = 1
        for x in solutions:
            s = Solution(
                name=f"{gender} rooms generated {timezone.now().strftime('%Y-%m-%d %H:%M')} (#{i})",
                solution=json.dumps(x[2]),
                explanation=x[1]
            )

            s.save()
            i += 1