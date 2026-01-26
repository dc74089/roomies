import django
if 'setup' in dir(django): django.setup()

import random
import traceback
from collections import defaultdict

from django.utils import timezone
from tqdm import tqdm

from app.models import Person, Request, Solution, SiteConfig, Site, Room
from app.utils.evaluate import evaluate_solution_dict
from app.utils.hash import hash_solution

db = None
people_by_gender = None


def fill_db():
    """Build affinity database with weighted connections between people."""
    global db
    global people_by_gender

    people_by_gender = {
        "male": list(Person.objects.filter(gender="male")),
        "female": list(Person.objects.filter(gender="female")),
        "nb": list(Person.objects.filter(gender="nb"))
    }

    db = {person.id: {p.id: 0 for p in Person.objects.all()} for person in Person.objects.all()}

    for req in Request.objects.filter(type="attract"):
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="attract").exists():
            db[req.requestor.id][req.requestee.id] += 3
            db[req.requestee.id][req.requestor.id] += 3
        else:
            db[req.requestor.id][req.requestee.id] += 1
            db[req.requestee.id][req.requestor.id] += 1

    for req in Request.objects.filter(type="repel"):
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="repel").exists():
            db[req.requestor.id][req.requestee.id] -= 3
            db[req.requestee.id][req.requestor.id] -= 3
        else:
            db[req.requestor.id][req.requestee.id] -= 1
            db[req.requestee.id][req.requestor.id] -= 1

    for req in Request.objects.filter(type="forbid"):
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="forbid").exists():
            db[req.requestor.id][req.requestee.id] -= 10000
            db[req.requestee.id][req.requestor.id] -= 10000

    for req in Request.objects.filter(type="require"):
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="require").exists():
            db[req.requestor.id][req.requestee.id] += 100
            db[req.requestee.id][req.requestor.id] += 100


def get_student_priority(person):
    """
    Calculate priority for placing a student (higher = place first).

    Prioritizes students with:
    1. Require/forbid constraints (highest priority)
    2. Mutual attract requests
    3. Fewer total requests (less flexible)
    4. Repel constraints
    """
    priority = 0

    # Check for require/forbid constraints
    has_require = Request.objects.filter(requestor=person, type="require").exists()
    has_forbid = Request.objects.filter(requestor=person, type="forbid").exists()

    if has_require or has_forbid:
        priority += 1000

    # Count mutual attracts
    mutual_attracts = 0
    for req in Request.objects.filter(requestor=person, type="attract"):
        if Request.objects.filter(requestor=req.requestee, requestee=person, type="attract").exists():
            mutual_attracts += 1

    priority += mutual_attracts * 100

    # Inverse of request count (fewer requests = higher priority)
    num_requests = Request.objects.filter(requestor=person, type="attract").count()
    if num_requests > 0:
        priority += (10 / num_requests)

    # Check for repel constraints
    has_repel = Request.objects.filter(requestor=person, type="repel").exists()
    if has_repel:
        priority += 50

    return priority


def score_partial_solution(solution, capacities, gender, unplaced_people):
    """
    Score a partial solution.

    Combines:
    1. Actual score for placed students
    2. Heuristic penalty for remaining unplaced students
    """
    # Evaluate placed students
    placed_score, _ = evaluate_solution_dict(solution, gender)

    # Add heuristic for unplaced students based on their flexibility
    unplaced_penalty = 0
    for person in unplaced_people:
        # Students with more requests are harder to place well
        num_requests = Request.objects.filter(requestor=person, type="attract").count()
        unplaced_penalty += num_requests * 0.1

    return placed_score + unplaced_penalty


def beam_search(gender, beam_width=50):
    """
    Generate solution using beam search.

    Explores multiple placement paths simultaneously, keeping the best beam_width
    partial solutions at each step.

    Args:
        gender: Gender to generate solution for
        beam_width: Number of partial solutions to keep in beam

    Returns:
        tuple: (score, explanation, solution_dict, capacities)
    """
    global people_by_gender, db

    # Set up rooms
    capacities = {}
    rooms = []

    site = Site.objects.get(id=SiteConfig.objects.get(id="site").num)
    blocks = site.get_site().get("blocks")

    for block in blocks:
        if block.get("gender") != gender: continue

        i = 1
        for _ in range(int(block["room_count"])):
            name = f"{block.get('name')} #{i:02d}"
            rooms.append(name)
            capacities[name] = int(block.get("room_capacity"))
            i += 1

    # Get people and sort by priority
    people = list(people_by_gender[gender])

    # Calculate priorities
    people_with_priority = [(p, get_student_priority(p)) for p in people]
    people_with_priority.sort(key=lambda x: x[1], reverse=True)

    # Add some randomization to avoid always placing in same order
    # Group by priority buckets and shuffle within buckets
    priority_buckets = defaultdict(list)
    for person, priority in people_with_priority:
        bucket = int(priority / 100)  # Group into buckets of 100
        priority_buckets[bucket].append(person)

    sorted_people = []
    for bucket in sorted(priority_buckets.keys(), reverse=True):
        bucket_people = priority_buckets[bucket]
        random.shuffle(bucket_people)
        sorted_people.extend(bucket_people)

    # Initialize beam with empty solution
    beam = [({room: [] for room in rooms}, 0)]  # (solution_dict, score)

    # Place each student
    for student_idx, person in enumerate(tqdm(sorted_people, desc="Beam search placement")):
        candidates = []

        # For each partial solution in beam
        for solution, _ in beam:
            # Try placing person in each room that has space
            for room in rooms:
                if len(solution[room]) >= capacities[room]:
                    continue

                # Create new solution with person in this room
                new_solution = {r: solution[r][:] for r in rooms}
                new_solution[room].append(person.id)

                # Score this partial solution
                unplaced = sorted_people[student_idx + 1:]
                score = score_partial_solution(new_solution, capacities, gender, unplaced)

                candidates.append((new_solution, score))

        # Keep only top beam_width candidates
        candidates.sort(key=lambda x: x[1])
        beam = candidates[:beam_width]

        # If beam is empty, we have a problem
        if not beam:
            raise Exception("Beam became empty - no valid placements found")

    # Return best complete solution
    best_solution, _ = beam[0]
    score, explanation = evaluate_solution_dict(best_solution, gender)

    return score, explanation, best_solution, capacities


def generate_and_save(n, gender):
    """Generate n solutions and save the best unique ones."""
    try:
        out = []
        fill_db()

        solutions = []
        hashes = []
        best_score = 2 ** 30

        for _ in tqdm(range(n), desc=f"Generating {gender} solutions"):
            soln = beam_search(gender.lower())

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
            score, explanation, solution_dict, capacities = x
            s = Solution(
                name=f"{gender} rooms generated {timezone.now().strftime('%Y-%m-%d %H:%M')} (#{i})",
                gender=gender.lower(),
                site=Site.objects.get(id=SiteConfig.objects.get(id="site").num),
                explanation=explanation,
                strategy="Beam Search",
                score=score
            )

            s.save()
            s.refresh_from_db()

            for room, ids in solution_dict.items():
                r = Room(
                    internal_name=room,
                    solution=s,
                    capacity=capacities[room],
                )

                r.save()

                for id in ids:
                    r.people.add(Person.objects.get(id=id))

                r.save()

            i += 1

            out.append(s.id)

        return out
    except:
        print("BEAM SEARCH ERROR")
        print(traceback.format_exc())


def generate_solutions(n):
    """Generate solutions for both Male and Female genders."""
    try:
        out = []

        for gender in ("Male", "Female"):
            out.extend(generate_and_save(n, gender))

        return out
    except:
        print("BEAM SEARCH ERROR")
        print(traceback.format_exc())
