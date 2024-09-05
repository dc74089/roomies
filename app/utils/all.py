import concurrent.futures

from app.models import Solution
from app.utils import graphy, greedyroom, sum, swap


def do_all():
    solns = []

    solns.extend(graphy.generate_solutions())
    solns.extend(greedyroom.generate_solutions(10000))
    solns.extend(sum.generate_solutions(10000))

    for sid in solns:
        swap.tune_solution_by_id(sid, 10)


def run_in_parallel():
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(graphy.generate_solutions),
            executor.submit(greedyroom.generate_and_save, 10000, "Male"),
            executor.submit(greedyroom.generate_and_save, 10000, "Female"),
            executor.submit(sum.generate_and_save, 10000, "Male"),
            executor.submit(sum.generate_and_save, 10000, "Female"),
        ]

        executor.shutdown(wait=True)

        tune_futures = tune_in_parallel()

    return futures, tune_futures


def tune_in_parallel():
    solns = list(Solution.objects.filter(tuned=False))

    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        futures = []

        for soln in solns:
            futures.append(executor.submit(swap.tune_solution_by_id, soln, 10))

        executor.shutdown(wait=True)

        return futures
