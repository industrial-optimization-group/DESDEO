# test_adm.py 
import numpy as np
from desdeo.problem.testproblems import river_pollution_problem
from desdeo.tools import PyomoIpoptSolver, payoff_table_method
from desdeo.adm import ADMAfsar, ADMChen

np.random.seed(42)

# Prepare problem
print("Loading river_pollution problem (4 objectives)...")
problem = river_pollution_problem(five_objective_variant=False)
ideal, nadir = payoff_table_method(problem, solver=PyomoIpoptSolver)
problem = problem.update_ideal_and_nadir(ideal, nadir)
print(f"  Ideal: {list(problem.get_ideal_point().values())}")
print(f"  Nadir: {list(problem.get_nadir_point().values())}")

# Simulated Pareto Front (5 solutions x 4 objectives)
# Values within the range of the river_pollution problem (maximization)
front = np.array([
    [-6.34, -3.44, -7.50,  0.00],
    [-6.10, -3.20, -5.00, -3.50],
    [-5.80, -3.10, -3.00, -6.00],
    [-5.50, -2.95, -1.00, -8.00],
    [-4.75, -2.85, -0.32, -9.71],
])
print(f"  Simulated front: {front.shape}")

# Test ADMAfsar 
print("TEST ADMAfsar")
print("  Parameters: problem, it_learning_phase=3, it_decision_phase=2,")
print("              number_of_vectors=10")
try:
    adm = ADMAfsar(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        number_of_vectors=10,   # required for create_simplex
    )
    print(f"  Created OK | max_iterations={adm.max_iterations} | "
          f"reference_vectors.shape={adm.reference_vectors.shape}")
    print(f"  Initial preference: {adm.preference}")

    print("\n  Iterating:")
    for i in range(adm.max_iterations):
        has = adm.has_next()
        phase = "learning" if adm.iteration_counter < adm.it_learning_phase else "decision"
        pref = adm.get_next_preference(front, preference_type="reference_point")
        print(f"    it={i+1} | phase={phase} | has_next={has} | pref={np.round(pref, 3)}")

    print(f"\n  has_next() after the loop: {adm.has_next()}")
    print("  ADMAfsar: WORKS")

except Exception as e:
    import traceback
    print(f"  ADMAfsar: ERROR — {type(e).__name__}: {e}")
    traceback.print_exc()

# Test ADMChen 
print("TEST ADMChen")
print("  Parameters: problem, it_learning_phase=3, it_decision_phase=2,")
print("              pareto_front=front")
try:
    adm_chen = ADMChen(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        pareto_front=front,     # required in ADMChen
    )
    print(f"  Created OK | max_iterations={adm_chen.max_iterations}")
    print(f"  Initial preference: {np.round(adm_chen.preference, 3)}")
    print(f"  UF_max={adm_chen.UF_max:.4f} | UF_opt={adm_chen.UF_opt:.4f}")

    print("\n  Iterating:")
    for i in range(adm_chen.max_iterations - 1):  # -1 because the __init__ already counts as 1
        has = adm_chen.has_next()
        phase = "learning" if adm_chen.iteration_counter < adm_chen.it_learning_phase else "decision"
        pref = adm_chen.get_next_preference(front)
        print(f"    it={i+1} | phase={phase} | has_next={has} | pref={np.round(pref, 3)}")

    print(f"\n  has_next() after the loop: {adm_chen.has_next()}")
    print("  ADMChen: WORKS")

except Exception as e:
    import traceback
    print(f"  ADMChen: ERROR — {type(e).__name__}: {e}")
    traceback.print_exc()

print("Test completed.")