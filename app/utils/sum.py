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

    people = list(Person.objects.filter(gender=gender))
    random.shuffle(people)

    seeds = people[:settings.ROOMS]

    for seed in seeds:
        out[str(uuid.uuid4())] = [seed.id]
        placed.append(seed)

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
    for gender in ("male", "female"):
        solutions = []
        for _ in tqdm(range(n)):
            solutions.append((generate_solution(gender)))

        solutions = sorted(solutions, key=lambda x: x[0])
        print(solutions[0][1])

        s = Solution(
            name=f"{gender} rooms generated {timezone.now().isoformat()}",
            solution=json.dumps(solutions[0][2]),
            explanation=solutions[0][1]
        )

        s.save()