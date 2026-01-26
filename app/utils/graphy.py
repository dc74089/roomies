import django
if 'setup' in dir(django): django.setup()

import random
import traceback

import networkx as nx
from django.utils import timezone
from tqdm import tqdm

from app.models import Person, Request, Solution, SiteConfig, Site, Room
from app.utils.evaluate import evaluate_solution_dict
from app.utils.hash import hash_solution


def build_affinity_db():
    """Build affinity database similar to greedysmart.py"""
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

    return db


def calculate_affinity_to_room(person_id, room_person_ids, affinity_db):
    """Calculate total affinity of a person to everyone currently in a room"""
    return sum(affinity_db[person_id][room_id] for room_id in room_person_ids)


def assign_community_to_rooms(community_person_ids, available_rooms, affinity_db):
    """
    Assign a community to rooms, trying to keep members together.
    Returns updated available_rooms dict and assignments made.
    """
    assignments = []
    remaining = list(community_person_ids)

    # Sort remaining by total internal community affinity (most connected first)
    remaining.sort(key=lambda p: sum(affinity_db[p][other] for other in community_person_ids), reverse=True)

    for room_name in available_rooms:
        if not remaining:
            break

        room_capacity = available_rooms[room_name]['capacity']
        room_current = available_rooms[room_name]['current']
        room_space = room_capacity - len(room_current)

        if room_space <= 0:
            continue

        # Fill this room with as many community members as possible
        to_place = remaining[:room_space]
        for person_id in to_place:
            room_current.append(person_id)
            assignments.append((room_name, person_id))

        remaining = remaining[room_space:]

    return assignments, remaining


def generate_solution(gender):
    """
    Generate solution using Louvain community detection, then assign communities
    to actual rooms with proper capacities.
    """
    affinity_db = build_affinity_db()

    # Build graph for community detection
    G = nx.Graph()
    people = list(Person.objects.filter(gender=gender))

    for person in people:
        G.add_node(person.id)

    # Add edges for attract requests (weighted by mutual vs one-way)
    for req in Request.objects.filter(requestor__gender=gender, type="attract"):
        if not G.has_edge(req.requestor.id, req.requestee.id):
            weight = 3 if Request.objects.filter(
                requestor=req.requestee, requestee=req.requestor, type="attract"
            ).exists() else 1
            G.add_edge(req.requestor.id, req.requestee.id, weight=weight)

    # Detect communities using Louvain
    communities = nx.community.louvain_communities(G, seed=random.randint(0, 1000000))

    # Get actual room configuration
    site = Site.objects.get(id=SiteConfig.objects.get(id="site").num)
    blocks = site.get_site().get("blocks")

    available_rooms = {}
    room_order = []

    for block in blocks:
        if block.get("gender") != gender:
            continue

        for i in range(1, int(block["room_count"]) + 1):
            room_name = f"{block.get('name')} #{i:02d}"
            available_rooms[room_name] = {
                'capacity': int(block.get("room_capacity")),
                'current': []
            }
            room_order.append(room_name)

    # Sort communities by size (largest first) to handle them efficiently
    communities = sorted(communities, key=len, reverse=True)

    # Assign communities to rooms
    unplaced = []

    for community in communities:
        community_ids = [p for p in community]
        assignments, remaining = assign_community_to_rooms(community_ids, available_rooms, affinity_db)
        unplaced.extend(remaining)

    # Place any unplaced students using greedy affinity-based placement
    random.shuffle(unplaced)

    for person_id in unplaced:
        best_room = None
        best_affinity = -float('inf')

        for room_name in room_order:
            room_capacity = available_rooms[room_name]['capacity']
            room_current = available_rooms[room_name]['current']

            if len(room_current) >= room_capacity:
                continue

            affinity = calculate_affinity_to_room(person_id, room_current, affinity_db)

            if affinity > best_affinity:
                best_affinity = affinity
                best_room = room_name

        if best_room:
            available_rooms[best_room]['current'].append(person_id)

    # Convert to solution format
    solution_dict = {room_name: data['current'] for room_name, data in available_rooms.items()}
    capacities = {room_name: data['capacity'] for room_name, data in available_rooms.items()}

    score, explanation = evaluate_solution_dict(solution_dict, gender)

    return score, explanation, solution_dict, capacities


def generate_and_save(n, gender):
    try:
        solutions = []
        hashes = []
        best_score = 2 ** 30

        for _ in tqdm(range(n), desc=f"Generating {gender} solutions"):
            soln = generate_solution(gender.lower())

            if soln[0] < best_score:
                best_score = soln[0]
                solutions = []
                hashes = []
                print(f"\nNew best score: {soln[0]}")

            if soln[0] == best_score and hash_solution(soln[2]) not in hashes:
                solutions.append(soln)
                hashes.append(hash_solution(soln[2]))
                print(f"\nSaving solution with score {soln[0]}")

        print(f"Found {len(solutions)} equivalent solutions with score {best_score}")

        out = []
        i = 1
        for x in solutions:
            score, explanation, solution_dict, capacities = x
            s = Solution(
                name=f"{gender} rooms generated {timezone.now().strftime('%Y-%m-%d %H:%M')} (#{i})",
                gender=gender.lower(),
                site=Site.objects.get(id=SiteConfig.objects.get(id="site").num),
                explanation=explanation,
                strategy="Graph Community (Louvain)",
                score=score
            )

            s.save()
            s.refresh_from_db()

            for room_name, ids in solution_dict.items():
                r = Room(
                    internal_name=room_name,
                    solution=s,
                    capacity=capacities[room_name],
                )

                r.save()

                for person_id in ids:
                    r.people.add(Person.objects.get(id=person_id))

                r.save()

            i += 1
            out.append(s.id)

        return out
    except:
        print("GRAPHY ERROR")
        print(traceback.format_exc())
        return []


def generate_solutions(n=10000):
    """Generate n solutions for each gender using graph community detection"""
    try:
        out = []

        for gender in ("Male", "Female"):
            out.extend(generate_and_save(n, gender))

        return out
    except:
        print("GRAPHY ERROR")
        print(traceback.format_exc())
        return []
