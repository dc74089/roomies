import itertools
import json
import math
import random
import signal
import traceback

from django.conf import settings
from django.utils import timezone
from tqdm import tqdm

from app.models import Solution, SiteConfig
from app.utils.evaluate import evaluate_solution

stop = False


def do_stop(_1, _2):
    global stop
    stop = True
    print("\n\nWill stop after this iteration\n")


def tune_solution(solution, gender, depth, capacities, strategy="?"):
    global stop
    rooms = []
    inversion = {}

    for room in solution:
        rooms.append(room)

        for person in solution[room]:
            inversion[person] = room

    original_score, original_desc = evaluate_solution(
        {room: [x for x in inversion.keys() if inversion[x] == room] for room in rooms}, gender)

    i = 0
    swaps = 1

    signal.signal(signal.SIGINT, do_stop)

    while (depth == -1) or (depth > 0 and i < depth):
        if stop: break

        i += 1
        swaps = 0

        print(f"Iteration {i}")

        base, _desc = evaluate_solution({room: [x for x in inversion.keys() if inversion[x] == room] for room in rooms},
                                        gender)

        if depth == -1 and base < 1000:
            print("All students have at least one request satisfied! Exiting.")
            break

        shuffled_keys = list(inversion.keys())
        random.shuffle(shuffled_keys)

        print("Shuffling into empty rooms")
        for p in tqdm(shuffled_keys):
            for room in rooms:
                if sum(x == room for x in inversion.values()) >= capacities[room]: continue
                old = inversion[p]
                inversion[p] = room

                new, _desc = evaluate_solution(
                    {room: [x for x in inversion.keys() if inversion[x] == room] for room in rooms}, gender)

                if base <= new:  # If base better than new, swap back
                    inversion[p] = old
                else:
                    print(f"\n{base} -> {new}")
                    base = new
                    swaps += 1

        base, _desc = evaluate_solution({room: [x for x in inversion.keys() if inversion[x] == room] for room in rooms},
                                        gender)

        print("Testing swaps")
        for a, b in tqdm(itertools.combinations(shuffled_keys, 2), total=math.comb(len(inversion.keys()), 2)):
            if inversion[a] == inversion[b]: continue

            tmp = inversion[a]
            inversion[a] = inversion[b]
            inversion[b] = tmp

            new, _desc = evaluate_solution(
                {room: [x for x in inversion.keys() if inversion[x] == room] for room in rooms}, gender)

            if base <= new:  # If base better than new, swap back
                tmp = inversion[a]
                inversion[a] = inversion[b]
                inversion[b] = tmp
            else:
                print(f"\n{base} -> {new}")
                base = new
                swaps += 1

        print(f"Did {swaps} swaps\n")

        if swaps == 0: break

    final = {room: [x for x in inversion.keys() if inversion[x] == room] for room in rooms}
    final_score, final_desc = evaluate_solution(final, gender)

    s = Solution(
        name=f"Tuned {gender} rooms generated {timezone.now().strftime('%Y-%m-%d %H:%M')}",
        solution=json.dumps(final),
        explanation=f"Score went from {original_score} to {final_score}. \n\n"
                    f"Orig: {original_desc} \n\n"
                    f"New: {final_desc}",
        strategy=f"Tuned {strategy}"
    )

    s.save()

    return s


def tune_solution_by_id(id, depth):
    try:
        s = Solution.objects.get(id=id)
        soln = s.get_solution()
        caps = s.get_capacities()
        gender = "female" if "female" in s.name.lower() else "male"

        x = tune_solution(soln, gender, depth, caps, s.strategy)

        s.tuned = True
        s.save()

        return x
    except:
        print("SWAP ERROR")
        print(traceback.format_exc())
