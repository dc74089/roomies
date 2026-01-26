import django
if 'setup' in dir(django): django.setup()

import concurrent.futures
from django.db import connection

from app.models import Solution
from app.utils import graphy, sum, swap, greedysmart, anneal


def do_all(depth=10000):
    solns = []

    solns.extend(graphy.generate_solutions(depth))
    solns.extend(greedysmart.generate_solutions(depth))
    solns.extend(sum.generate_solutions(depth))
    solns.extend(anneal.generate_solutions(depth))

    for sid in solns:
        swap.tune_solution_by_id(sid, 10)


def run_in_parallel(gender=None, depth=10000):
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        if gender == "male":
            futures = [
                executor.submit(graphy.generate_solutions),
                executor.submit(greedysmart.generate_and_save, depth, "Male"),
                executor.submit(sum.generate_and_save, depth, "Male"),
                executor.submit(anneal.generate_and_save, depth, "Male"),
            ]
        elif gender == "female":
            futures = [
                executor.submit(graphy.generate_solutions),
                executor.submit(greedysmart.generate_and_save, depth, "Female"),
                executor.submit(sum.generate_and_save, depth, "Female"),
                executor.submit(anneal.generate_and_save, depth, "Female"),
            ]
        else:
            futures = [
                executor.submit(graphy.generate_solutions),
                executor.submit(greedysmart.generate_and_save, depth, "Male"),
                executor.submit(greedysmart.generate_and_save, depth, "Female"),
                executor.submit(sum.generate_and_save, depth, "Male"),
                executor.submit(sum.generate_and_save, depth, "Female"),
                executor.submit(anneal.generate_and_save, depth, "Male"),
                executor.submit(anneal.generate_and_save, depth, "Female"),
            ]

        executor.shutdown(wait=True)

    tune_futures = tune_in_parallel()

    return futures, tune_futures


def tune_helper(soln_id, n):
    django.setup()
    swap.tune_solution_by_id(soln_id, n)


def tune_in_parallel():
    solns = list(Solution.objects.filter(tuned=False))

    django.db.connections.close_all()

    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        futures = []

        for soln in solns:
            futures.append(executor.submit(tune_helper, soln.id, 100))

    executor.shutdown(wait=True)

    return futures
