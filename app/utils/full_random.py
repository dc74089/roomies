import json

from django.conf import settings
from tqdm import tqdm

from app.models import Person, Solution
from app.utils import swap, evaluate


def generate_random_room(gender):
    rooms = {}

    for i in range(settings.ROOMS):
        rooms[f"Room {i + 1}"] = []

    i = 0
    for person in Person.objects.filter(gender=gender):
        i += 1

        rooms[f"Room {i}"].append(person.id)

        i %= settings.ROOMS

    s = Solution(
        name=f"Random {gender} rooms",
        solution=json.dumps(rooms),
        explanation="Random Rooms"
    )

    s.save()

    return s.id


def generate_and_tune(gender, n):
    touched_ids = []
    best = None
    best_score = 9999999999999

    for _ in tqdm(range(n), colour="green"):
        rand = generate_random_room(gender)
        touched_ids.append(rand)

        new_soln: Solution = swap.tune_solution_by_id(rand, 100)
        score, _ = evaluate.evaluate_solution(new_soln.get_solution(), gender)

        Solution.objects.get(id=rand).delete()

        if score < best_score:
            if best:
                best.delete()

            best = new_soln
            best_score = score
        else:
            new_soln.delete()
