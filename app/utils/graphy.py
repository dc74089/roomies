from pprint import pprint

import networkx as nx
from django.conf import settings

from app.models import Person, Request, Solution
from app.utils.evaluate import evaluate_solution


def ideal_splits(rooms):
    out = list(rooms)

    while any([len(room) > settings.ROOM_MAX_CAPACITY for room in rooms]):
        pprint("ITER_START")
        pprint(rooms)
        out = []
        for room in rooms:
            if len(room) <= settings.ROOM_MAX_CAPACITY:
                out.append(room)
                continue

            G = nx.Graph()

            for p in room:
                G.add_node(p)

                for req in p.requests.all():
                    if req.requestee not in room: continue
                    if not G.has_edge(p, req.requestee):
                        G.add_edge(
                            p,
                            req.requestee,
                            weight=2 if Request.objects.filter(requestor=req.requestee, requestee=p).exists() else 1
                        )

            x = nx.community.kernighan_lin_bisection(G)
            y = list(x)

            out.extend(y)
        rooms = list(out)

    return {f"Room {n}": [s.id for s in stus] for n, stus in zip(range(1, 1 + len(out)), out)}


def split_by_id(soln_id):
    s = Solution.objects.get(id=soln_id)
    gender = "female" if "female" in s.name.lower() else "male"
    rooms = s.get_solution()

    out = list(rooms)

    for room in rooms:
        if len(room) * 2 <= settings.ROOM_MAX_CAPACITY:
            out.append(room)
            continue

        G = nx.Graph()

        for p in room:
            G.add_node(p)

            for req in p.requests.all():
                if req.requestee not in room: continue
                if not G.has_edge(p, req.requestee):
                    G.add_edge(
                        p,
                        req.requestee,
                        weight=4 if Request.objects.filter(requestor=req.requestee, requestee=p).exists() else 1
                    )

        x = nx.community.kernighan_lin_bisection(G)
        y = list(x)

        out.extend(y)

    new_soln = {f"Room {n}": [s.id for s in stus] for n, stus in zip(range(1, 1 + len(out)), out)}
    score = evaluate_solution(new_soln, gender)

    split_soln = Solution(
        name=f"Graphy Even-Split {gender} Rooms",
        strategy="Louvain B Split",
        explanation=f"Louvain B Split scores: {score[1]}"
    )

    split_soln.set_solution(new_soln)
    split_soln.save()


def generate_solution(gender='female'):
    G = nx.DiGraph()

    for s in Person.objects.filter(gender=gender):
        G.add_node(s)

    for req in Request.objects.filter(requestor__gender=gender):
        G.add_edge(req.requestor, req.requestee)

    x = nx.community.louvain_partitions(G)
    y = list(x)

    soln2 = {f"Room {n}": [s.id for s in stus] for n, stus in zip(range(1, 1 + len(y[1])), y[1])}
    soln2_score = evaluate_solution(soln2, gender)

    s2 = Solution(
        name=f"Graphy {gender} Rooms",
        strategy="Louvain B",
        explanation=f"Louvain B scores: {soln2_score[1]}"
    )

    s2.set_solution(soln2)
    s2.save()

    z = ideal_splits(y[1])
    z_score = evaluate_solution(z, gender)

    zs = Solution(
        name=f"Graphy Split {gender} Rooms",
        strategy="Louvain B Split",
        explanation=f"Louvain B Split scores: {z_score[1]}"
    )

    zs.set_solution(z)
    zs.save()


def generate_solutions():
    generate_solution("male")
    generate_solution("female")
