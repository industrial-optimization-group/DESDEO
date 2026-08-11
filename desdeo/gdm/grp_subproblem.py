import warnings
import numpy as np
from desdeo.problem.schema import (
    Variable,
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem
)

def additive_preference_constraints(
    rps: np.ndarray,
    cip: np.ndarray,
    projections: np.ndarray = None
) -> tuple[list[Variable], list[Constraint]]:
    """Generates DESDEO constraints for the additive local preference model.

    Formulates the evaluation score `s_m` for each decision maker by assuming
    indifference curves that are strictly orthogonal to their preferred direction of improvement.
    If `projections` are provided, they are used to scale the evaluations instead of the
    original reference points, which neutralizes the influence of highly optimistic outliers.

    Args:
        rps (np.ndarray): An array of shape (m_dms, k_objs) containing the individual
            reference points of the decision makers.
        cip (np.ndarray): The current iteration point in the objective space.
        projections (np.ndarray | None, optional): An array of shape (m_dms, k_objs)
            containing the Pareto optimal projections of the reference points. Defaults to None.

    Returns:
        tuple[list[Variable], list[Constraint]]: A tuple containing an empty list of auxiliary
            variables (for interface consistency) and a list of DESDEO `Constraint` objects
            representing the additive preference evaluations.
    """
    m_dms, k_objs = rps.shape
    scale_points = projections if projections is not None else rps
    constraints = []

    for m in range(m_dms):
        denom = np.sum((scale_points[m, :] - cip)**2)
        if denom == 0:
            denom = 1e-8  # Should not happen, but prevents division by zero

        terms = []
        for k in range(k_objs):
            coeff = (scale_points[m, k] - cip[k]) / denom
            terms.append(f"({coeff} * (cgrp_{k} - {cip[k]}))")

        s_expr = " + ".join(terms)
        constraints.append(
            Constraint(
                name=f"Additive_pref_DM_{m}",
                symbol=f"c_pref_{m}",
                cons_type=ConstraintTypeEnum.EQ,
                func=f"s_{m} - ({s_expr})",
                is_linear=True,
                is_twice_differentiable=True,
            )
        )

    return [], constraints


def symmetric_cones_preference_constraints(
    rps: np.ndarray,
    cip: np.ndarray,
    projections: np.ndarray = None,
    cone_alpha: float = 0.5
) -> tuple[list[Variable], list[Constraint]]:
    """Generates auxiliary variables and constraints for the symmetric cones preference model.

    This model strictly penalizes candidate points that deviate laterally from a decision maker's 
    preferred direction of improvement. It utilizes epsilon smoothing (1e-8) and dot-product 
    projections to ensure the resulting non-linear constraints remain twice-differentiable and 
    numerically stable for gradient-based solvers (like IPOPT).

    Args:
        rps (np.ndarray): An array of shape (m_dms, k_objs) containing the individual 
            reference points of the decision makers.
        cip (np.ndarray): The current iteration point in the objective space.
        projections (np.ndarray | None, optional): An array of shape (m_dms, k_objs) 
            containing the Pareto optimal projections of the reference points for scaling. 
            Defaults to None.
        cone_alpha (float, optional): A parameter controlling the width (angle) of the 
            symmetric preference cone. Defaults to 0.5.

    Returns:
        tuple[list[Variable], list[Constraint]]: A tuple containing a list of auxiliary 
            DESDEO `Variable` objects and a list of DESDEO `Constraint` objects formulating 
            the non-linear geometric cone model.
    """
    m_dms, k_objs = rps.shape
    scale_points = projections if projections is not None else rps

    aux_variables = []
    constraints = []
    cone_ratio = cone_alpha / (1.0 - cone_alpha)
    eps = 1e-8

    for m in range(m_dms):
        d_m = scale_points[m, :] - cip
        d_m_norm_sq = np.sum(d_m**2)

        if d_m_norm_sq == 0:
            d_m_norm_sq = eps

        d_m_hat = d_m / np.sqrt(d_m_norm_sq)

        # --- 1. Auxiliary Variables ---
        aux_variables.append(Variable(name=f"t_DM_{m}", symbol=f"t_{m}", variable_type="real", lowerbound=-1000, upperbound=1000, initial_value=1.0))
        aux_variables.append(Variable(name=f"norm_v_DM_{m}", symbol=f"norm_v_{m}", variable_type="real", lowerbound=0.0, upperbound=1000, initial_value=0.0))

        for k in range(k_objs):
            aux_variables.append(Variable(name=f"b_{m}_{k}", symbol=f"b_{m}_{k}", variable_type="real",
                                 lowerbound=-1000, upperbound=1000, initial_value=cip[k]))
            aux_variables.append(Variable(name=f"v_{m}_{k}", symbol=f"v_{m}_{k}", variable_type="real", lowerbound=-1000, upperbound=1000, initial_value=0.0))
            aux_variables.append(Variable(name=f"x_{m}_{k}", symbol=f"x_{m}_{k}", variable_type="real",
                                 lowerbound=-1000, upperbound=1000, initial_value=scale_points[m, k]))

        # --- 2. Geometric Constraints ---
        # 2a. b_m lies on direction vector
        for k in range(k_objs):
            constraints.append(Constraint(
                name=f"Line_Eq_b_{m}_{k}", symbol=f"c_b_{m}_{k}", cons_type=ConstraintTypeEnum.EQ,
                func=f"b_{m}_{k} - ({cip[k]} + t_{m} * {d_m[k]})", is_linear=True, is_twice_differentiable=True
            ))

        # 2b. Orthogonality
        ortho_terms = " + ".join([f"({d_m[k]} * (cgrp_{k} - b_{m}_{k}))" for k in range(k_objs)])
        constraints.append(Constraint(
            name=f"Orthogonality_{m}", symbol=f"c_ortho_{m}", cons_type=ConstraintTypeEnum.EQ,
            func=ortho_terms, is_linear=True, is_twice_differentiable=True
        ))

        # 2c. Deviation vector v_m
        for k in range(k_objs):
            constraints.append(Constraint(
                name=f"Dev_Vec_{m}_{k}", symbol=f"c_v_{m}_{k}", cons_type=ConstraintTypeEnum.EQ,
                func=f"v_{m}_{k} - (cgrp_{k} - b_{m}_{k})", is_linear=True, is_twice_differentiable=True
            ))

        # 2d. Magnitude of v_m (Non-Linear Quadratic constraint + 1e-8 epsilon smoothing)
        v_sq_terms = " + ".join([f"v_{m}_{k}**2" for k in range(k_objs)])
        constraints.append(Constraint(
            name=f"Norm_v_{m}", symbol=f"c_normv_{m}", cons_type=ConstraintTypeEnum.EQ,
            func=f"norm_v_{m}**2 - ({v_sq_terms} + {eps})",
            is_linear=False, is_twice_differentiable=True
        ))

        # 2e. Equivalent point x_m
        for k in range(k_objs):
            constraints.append(Constraint(
                name=f"Eq_Point_{m}_{k}", symbol=f"c_x_{m}_{k}", cons_type=ConstraintTypeEnum.EQ,
                func=f"x_{m}_{k} - (b_{m}_{k} - norm_v_{m} * {cone_ratio} * {d_m_hat[k]})",
                is_linear=True, is_twice_differentiable=True
            ))

        # 2f. Final score s_m (Dot product normalized across all k dimensions)
        s_terms = " + ".join([f"({d_m[k]} * (x_{m}_{k} - {cip[k]}))" for k in range(k_objs)])
        constraints.append(Constraint(
            name=f"Cone_Eval_{m}", symbol=f"c_pref_{m}", cons_type=ConstraintTypeEnum.EQ,
            func=f"s_{m} - (({s_terms}) / {d_m_norm_sq})",
            is_linear=True, is_twice_differentiable=True
        ))

    return aux_variables, constraints


def maxmin_fairness_constraints(n_dms: int) -> list[Constraint]:
    """Generates constraints linking the fairness variable to individual satisfaction scores.

    Creates linear bounds of the form `alpha <= s_m` for each decision maker. This allows 
    the optimization solver to evaluate the Rawlsian fairness of a candidate group reference point.

    Args:
        n_dms (int): The total number of decision makers in the group.

    Returns:
        list[Constraint]: A list of DESDEO `Constraint` objects enforcing the max-min bounds.
    """
    constraints = []
    for m in range(n_dms):
        constraints.append(
            Constraint(
                name=f"MaxMin_Bound_DM_{m}", symbol=f"c_mm_{m}", cons_type=ConstraintTypeEnum.LTE,
                func=f"alpha - s_{m}", is_linear=True, is_twice_differentiable=True,
            )
        )
    return constraints

def maxmin_fairness_objective() -> list[Objective]:
    """Generates the objective function to maximize group fairness.

    Formulates the objective to maximize the `alpha` variable, which represents the 
    satisfaction score of the worst-off decision maker, achieving a max-min equilibrium.
    Note:
        Because this is defined with `maximize=True`, DESDEO's `PyomoIpoptSolver` 
        (which strictly minimizes) will automatically generate a mathematically flipped 
        version of this objective. **When calling the solver, you MUST append the `_min` 
        suffix to the objective name**, like so: `solver.solve("obj_alpha_min")`. 
        Calling `solver.solve("obj_alpha")` will incorrectly minimize the fairness.
    Returns:
        list[Objective]: A list containing a single DESDEO `Objective` set to maximize.
    """
    return [
        Objective(
            name="Maximize_Minimum_Satisfaction", symbol="obj_alpha", func="alpha",
            maximize=True, objective_type=ObjectiveTypeEnum.analytical,
            is_linear=True, is_twice_differentiable=True,
        )
    ]


def build_grp_subproblem(
    rps: np.ndarray,
    cip: np.ndarray,
    ideal: np.ndarray,
    preference_factory: callable,
    fairness_constraints_factory: callable,
    fairness_objective_factory: callable,
    projections: np.ndarray = None
) -> Problem:
    """Assembles the Group Reference Point (GRP) subproblem into a solveable DESDEO Problem.

    Constructs the optimization problem required to find a fair collective direction of improvement. 
    It bounds the candidate GRP to the convex hull of the individual reference points (or projections) 
    and applies the specified local preference and fairness models. 

    Args:
        rps (np.ndarray): An array of shape (m_dms, k_objs) containing the individual reference points.
        cip (np.ndarray): The current iteration point in the objective space.
        ideal (np.ndarray): The ideal point of the multiobjective optimization problem.
        preference_factory (callable): A function (e.g., `additive_preference_constraints`) that 
            returns the auxiliary variables and constraints for the local preference model.
        fairness_constraints_factory (callable): A function that generates the bounding constraints 
            for the fairness operator.
        fairness_objective_factory (callable): A function that generates the fairness objective.
        projections (np.ndarray | None, optional): An array of Pareto optimal projections corresponding 
            to the reference points. Defaults to None.

    Returns:
        Problem: The fully assembled DESDEO `Problem` object, ready to be passed to a solver.
    """
    # Safety Check: Warn if objectives are not scaled to [0, 1]
    if np.any(cip < -0.01) or np.any(cip > 1.01) or np.any(rps < -0.01):
        warnings.warn(
            "GRP Subproblem expects objective values to be scaled to [0, 1]. "
            "Unscaled or disparately scaled data may cause numerical instability in gradient-based solvers like IPOPT."
        )

    m_dms, k_objs = rps.shape
    variables = []

    variables.append(Variable(name="Fairness_Alpha", symbol="alpha", variable_type="real", lowerbound=-10000, upperbound=10000, initial_value=0.0))

    for m in range(m_dms):
        variables.append(Variable(name=f"Weight_DM_{m}", symbol=f"w_{m}", variable_type="real", lowerbound=0.0, upperbound=1.0, initial_value=1.0/m_dms))
        variables.append(Variable(name=f"Satisfaction_DM_{m}", symbol=f"s_{m}", variable_type="real", lowerbound=-10000, upperbound=10000, initial_value=0.0))

    for k in range(k_objs):
        mean_k = np.mean(rps[:, k])
        variables.append(Variable(name=f"GRP_Coord_{k}", symbol=f"cgrp_{k}", variable_type="real", lowerbound=-10000, upperbound=10000, initial_value=mean_k))

    constraints = []

    w_sum_expr = " + ".join([f"w_{m}" for m in range(m_dms)])
    constraints.append(Constraint(
        name="Convexity_Weights", symbol="c_conv", cons_type=ConstraintTypeEnum.EQ, func=f"({w_sum_expr}) - 1", is_linear=True, is_twice_differentiable=True,
    ))

    for k in range(k_objs):
        cgrp_expr = " + ".join([f"({rps[m, k]} * w_{m})" for m in range(m_dms)])
        constraints.append(Constraint(
            name=f"GRP_Definition_{k}", symbol=f"c_cgrp_{k}", cons_type=ConstraintTypeEnum.EQ, func=f"cgrp_{k} - ({cgrp_expr})", is_linear=True, is_twice_differentiable=True,
        ))

    aux_vars, pref_constraints = preference_factory(rps, cip, projections)
    variables.extend(aux_vars)
    constraints.extend(pref_constraints)
    constraints.extend(fairness_constraints_factory(m_dms))

    return Problem(
        name="Group_Reference_Point_Subproblem",
        description="Linear algebraic formulation of the GRP preference aggregation",
        variables=variables,
        constraints=constraints,
        objectives=fairness_objective_factory()
    )


if __name__ == "__main__":
    from desdeo.problem.testproblems import zdt1
    from desdeo.problem import get_nadir_dict, get_ideal_dict, objective_dict_to_numpy_array
    from desdeo.tools.utils import PyomoIpoptSolver

    print("Initializing ZDT1 Problem Data...")
    problem = zdt1(30)
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    print(nadir)
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))

    all_rps = np.array([[0.1, 0.95], [0.5, 0.83], [0.9, 0.69], [0.6, 0.75]])
    cip = np.array([1.0, 1.0])

    print("\nBuilding DESDEO GRP Subproblem (Cones Model + Max-Min)...")
    grp_subproblem = build_grp_subproblem(
        rps=all_rps, cip=cip, ideal=ideal,
        preference_factory=symmetric_cones_preference_constraints,
        # preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    print("\nExecuting PyomoIpoptSolver...")
    solver = PyomoIpoptSolver(grp_subproblem)
    # IMPORTANT: Because IPOPT is a minimizer and our objective has maximize=True,
    # DESDEO requires us to target the automatically generated '_min' objective.
    # Forgetting the '_min' suffix will cause the solver to minimize fairness!
    result = solver.solve("obj_alpha_min")

    print("\n--- OPTIMIZATION RESULTS ---")
    print(f"Fairness Alpha (Min Satisfaction): {result.optimal_objectives['obj_alpha']:.4f}")
    print(f"Group Reference Point (GRP): [{result.optimal_variables['cgrp_0']:.4f}, {result.optimal_variables['cgrp_1']:.4f}]")
