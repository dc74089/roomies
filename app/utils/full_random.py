import json

from django.conf import settings
from tqdm import tqdm

from app.models import Person, Solution, SiteConfig, Site
from app.utils import swap, evaluate


def generate_random_room(gender):
    rooms = {}
    capacities = {}

    site = Site.objects.get(id=SiteConfig.objects.get(id="site").num)
    blocks = site.get_site().get("blocks")

    for block in blocks:
        if block.get("gender") != gender: continue

        i = 1
        for _ in range(int(block["room_count"])):
            name = f"{block.get('name')} #{i}"
            rooms[name] = []
            capacities[name] = int(block.get("room_capacity"))
            i += 1

    room_keys = list(rooms.keys())
    i = 0

    for person in Person.objects.filter(gender=gender).order_by("?"):
        rooms[room_keys[i]].append(person.id)

        i += 1
        i %= len(room_keys)

    s = Solution(
        name=f"Random {gender} rooms",
        solution=json.dumps(rooms),
        capacities=json.dumps(capacities),
        explanation="Random Rooms",
        strategy="Random"
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
