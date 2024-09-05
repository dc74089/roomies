import concurrent.futures

from app.utils import graphy, greedyroom, sum, swap


def do_all():
    solns = []

    solns.extend(graphy.generate_solutions())
    solns.extend(greedyroom.generate_solutions(10000))
    solns.extend(sum.generate_solutions(10000))

    for sid in solns:
        swap.tune_solution_by_id(sid, 10)


def run_in_parallel():
    tune_future_list = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(graphy.generate_solutions),
            executor.submit(greedyroom.generate_and_save, 10000, "Male"),
            executor.submit(greedyroom.generate_and_save, 10000, "Female"),
            executor.submit(sum.generate_and_save, 10000, "Male"),
            executor.submit(sum.generate_and_save, 10000, "Female"),
        ]

        for future in concurrent.futures.as_completed(futures):
            results = future.result()

            for result in results:
                tune_future_list.append(
                    executor.submit(swap.tune_solution_by_id, result, 10)
                )

        final_results = []
        for future in concurrent.futures.as_completed(tune_future_list):
            final_results.append(future.result())

    return final_results