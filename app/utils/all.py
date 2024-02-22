from app.utils import graphy, greedyroom, sum, swap


def do_all():
    solns = []

    # solns.extend(graphy.generate_solutions())
    solns.extend(greedyroom.generate_solutions(10000))
    solns.extend(sum.generate_solutions(9000))

    for sid in solns:
        swap.tune_solution_by_id(sid, 10)
