import django
if 'setup' in dir(django): django.setup()

import random
import math
import traceback

from django.utils import timezone
from tqdm import tqdm

from app.models import Person, Request, Solution, SiteConfig, Site, Room
from app.utils.evaluate import evaluate_solution_dict
from app.utils.hash import hash_solution

db = None
people_by_gender = None
request_cache = None
manual_requests = None


def fill_db():
    """Build affinity database and cache all requests for fast access."""
    global db, people_by_gender, request_cache, manual_requests

    people_by_gender = {
        "male": list(Person.objects.filter(gender="male")),
        "female": list(Person.objects.filter(gender="female")),
        "nb": list(Person.objects.filter(gender="nb"))
    }

    db = {person.id: {p.id: 0 for p in Person.objects.all()} for person in Person.objects.all()}

    # Cache all requests for incremental scoring
    request_cache = {}
    for person in Person.objects.all():
        request_cache[person.id] = {
            'attract': [],
            'repel': [],
            'forbid': [],
            'require': []
        }

    for req in Request.objects.filter(type="attract", manual=False):
        request_cache[req.requestor.id]['attract'].append(req.requestee.id)
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="attract").exists():
            db[req.requestor.id][req.requestee.id] += 3
            db[req.requestee.id][req.requestor.id] += 3
        else:
            db[req.requestor.id][req.requestee.id] += 1
            db[req.requestee.id][req.requestor.id] += 1

    for req in Request.objects.filter(type="repel"):
        request_cache[req.requestor.id]['repel'].append(req.requestee.id)
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="repel").exists():
            db[req.requestor.id][req.requestee.id] -= 3
            db[req.requestee.id][req.requestor.id] -= 3
        else:
            db[req.requestor.id][req.requestee.id] -= 1
            db[req.requestee.id][req.requestor.id] -= 1

    for req in Request.objects.filter(type="forbid"):
        request_cache[req.requestor.id]['forbid'].append(req.requestee.id)
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="forbid").exists():
            db[req.requestor.id][req.requestee.id] -= 10000
            db[req.requestee.id][req.requestor.id] -= 10000

    for req in Request.objects.filter(type="require"):
        request_cache[req.requestor.id]['require'].append(req.requestee.id)
        if Request.objects.filter(requestor=req.requestee, requestee=req.requestor, type="require").exists():
            db[req.requestor.id][req.requestee.id] += 100
            db[req.requestee.id][req.requestor.id] += 100

    # Cache manual requests
    manual_requests = []
    for req in Request.objects.filter(manual=True):
        manual_requests.append({
            'requestor': req.requestor.id,
            'requestee': req.requestee.id,
            'type': req.type
        })


def calculate_person_score(person_id, inversion):
    """Calculate score contribution for a single person based on their requests."""
    global request_cache

    if person_id not in request_cache:
        return 0

    person_room = inversion[person_id]
    attract_requests = request_cache[person_id]['attract']

    if not attract_requests:
        return 0

    num_failures = 0
    num_successes = 0

    for requestee_id in attract_requests:
        if requestee_id not in inversion:
            continue

        if inversion[requestee_id] == person_room:
            num_successes += 1
        else:
            num_failures += 1

    total_requests = num_successes + num_failures
    if total_requests == 0:
        return 0

    score = num_failures / total_requests

    # Add penalty if all requests failed
    if num_successes == 0:
        score += 1000

    return score


def calculate_manual_constraints_score(inversion):
    """Calculate penalty for manual constraint violations."""
    global manual_requests

    score = 0
    for req in manual_requests:
        requestor_id = req['requestor']
        requestee_id = req['requestee']
        req_type = req['type']

        if requestor_id not in inversion or requestee_id not in inversion:
            continue

        if req_type == 'forbid':
            if inversion[requestor_id] == inversion[requestee_id]:
                score += 1000000
        elif req_type == 'require':
            if inversion[requestor_id] != inversion[requestee_id]:
                score += 1000000

    return score


def helper(eligible, current_room_ids):
    """Find best person to add to current room based on affinity."""
    global db

    vals = {i: 0 for i in eligible}
    for person in eligible:
        for room_member_id in current_room_ids:
            vals[person] += db[person.id][room_member_id]

    return sorted(eligible, key=lambda x: vals[x], reverse=True)[0]


def generate_initial_solution(gender):
    """Generate initial solution using greedy approach."""
    global people_by_gender

    out = {}
    placed = []
    capacities = {}

    people = list(people_by_gender[gender])
    random.shuffle(people)

    site = Site.objects.get(id=SiteConfig.objects.get(id="site").num)
    blocks = site.get_site().get("blocks")

    for block in blocks:
        if block.get("gender") != gender: continue

        i = 1
        for _ in range(int(block["room_count"])):
            name = f"{block.get('name')} #{i:02d}"
            out[name] = []
            capacities[name] = int(block.get("room_capacity"))
            i += 1

    for room in out.keys():
        for _ in range(capacities[room]):
            if len(placed) == len(people): break

            eligible = [i for i in people if i not in placed]
            mvp: Person = helper(eligible, out[room])

            placed.append(mvp)
            out[room].append(mvp.id)

    return out, capacities


def simulated_annealing(gender, iterations=10000, initial_temp=100, cooling_rate=0.995):
    """
    Generate solution using simulated annealing with incremental scoring.

    Args:
        gender: Gender to generate solution for
        iterations: Number of iterations to run
        initial_temp: Starting temperature
        cooling_rate: Temperature decay rate (multiplicative)

    Returns:
        tuple: (score, explanation, solution_dict, capacities)
    """
    # Generate initial solution
    solution, capacities = generate_initial_solution(gender)

    # Create inversion map for faster lookups
    inversion = {}
    rooms = list(solution.keys())

    for room in rooms:
        for person_id in solution[room]:
            inversion[person_id] = room

    # Calculate initial score using full evaluation
    temp_solution = {room: [p for p in inversion.keys() if inversion[p] == room] for room in rooms}
    current_score, _ = evaluate_solution_dict(temp_solution, gender)
    best_score = current_score
    best_inversion = inversion.copy()

    temperature = initial_temp
    all_people = list(inversion.keys())

    for iteration in tqdm(range(iterations), desc=f"Annealing {gender}"):
        # Try a modification
        move_type = random.random()

        if move_type < 0.5:
            # Try moving someone to a room with space
            person = random.choice(all_people)
            old_room = inversion[person]

            # Find rooms with available capacity
            available_rooms = [
                room for room in rooms
                if sum(1 for p in inversion.values() if p == room) < capacities[room]
            ]

            if not available_rooms:
                continue

            new_room = random.choice(available_rooms)

            # Calculate score delta (only affected people need recalculation)
            # People affected: the person moving, their old roommates, their new roommates
            old_room_people = [p for p in all_people if inversion[p] == old_room]
            new_room_people = [p for p in all_people if inversion[p] == new_room]

            # Calculate old scores for affected people
            old_person_scores = sum(calculate_person_score(p, inversion) for p in set(old_room_people + new_room_people))
            old_manual_score = calculate_manual_constraints_score(inversion)

            # Make the move
            inversion[person] = new_room

            # Calculate new scores
            new_person_scores = sum(calculate_person_score(p, inversion) for p in set(old_room_people + new_room_people))
            new_manual_score = calculate_manual_constraints_score(inversion)

            # Calculate delta
            delta = (new_person_scores + new_manual_score) - (old_person_scores + old_manual_score)
            new_score = current_score + delta

            # Decide whether to accept
            if delta < 0:
                # Improvement
                current_score = new_score
                if new_score < best_score:
                    best_score = new_score
                    best_inversion = inversion.copy()
            elif temperature > 0 and random.random() < math.exp(-delta / temperature):
                # Accept worse solution
                current_score = new_score
            else:
                # Reject - revert
                inversion[person] = old_room

        else:
            # Try swapping two people
            person_a, person_b = random.sample(all_people, 2)
            room_a = inversion[person_a]
            room_b = inversion[person_b]

            if room_a == room_b:
                continue

            # Calculate score delta
            affected_people = [p for p in all_people if inversion[p] in [room_a, room_b]]
            old_person_scores = sum(calculate_person_score(p, inversion) for p in affected_people)
            old_manual_score = calculate_manual_constraints_score(inversion)

            # Make the swap
            inversion[person_a], inversion[person_b] = inversion[person_b], inversion[person_a]

            # Calculate new scores
            new_person_scores = sum(calculate_person_score(p, inversion) for p in affected_people)
            new_manual_score = calculate_manual_constraints_score(inversion)

            # Calculate delta
            delta = (new_person_scores + new_manual_score) - (old_person_scores + old_manual_score)
            new_score = current_score + delta

            # Decide whether to accept
            if delta < 0:
                # Improvement
                current_score = new_score
                if new_score < best_score:
                    best_score = new_score
                    best_inversion = inversion.copy()
            elif temperature > 0 and random.random() < math.exp(-delta / temperature):
                # Accept worse solution
                current_score = new_score
            else:
                # Reject - revert
                inversion[person_a], inversion[person_b] = inversion[person_b], inversion[person_a]

        # Cool down
        temperature *= cooling_rate

        # Early stopping if we find a perfect solution
        if best_score < 1000:
            break

    # Build final solution from best inversion
    best_solution = {room: [p for p in best_inversion.keys() if best_inversion[p] == room] for room in rooms}
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

        for _ in range(n):
            soln = simulated_annealing(gender.lower())

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
                strategy="Simulated Annealing",
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
        print("SIMULATED ANNEALING ERROR")
        print(traceback.format_exc())


def generate_solutions(n):
    """Generate solutions for both Male and Female genders."""
    try:
        out = []

        for gender in ("Male", "Female"):
            out.extend(generate_and_save(n, gender))

        return out
    except:
        print("SIMULATED ANNEALING ERROR")
        print(traceback.format_exc())
