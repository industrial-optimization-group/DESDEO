from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

def rocket_injector_design(original_version=False) -> Problem:
    """The rocekt injector design problem as published in Vaidyanathan, et al. (2003).

    The original version of the problem has 4 objectives. In Goel et al. (2007), the TW4 objective is dropped
    due to high correlation with one of the other objectives. Hence, the default version of the problem is the
    modified version with 3 objectives.

    Args:
        original_version (bool): If True, the original version of the problem with 4 objectives is returned.

    References:
        R. Vaidyanathan, K. Tucker, N. Papila, W. Shyy, CFD-Based Design Optimization For Single Element Rocket
        Injector, in: AIAA Aerospace Sciences Meeting, 2003, pp. 1-21.

        Goel, T., Vaidyanathan, R., Haftka, R. T., Shyy, W., Queipo, N. V., & Tucker, K. (2007).
        Response surface approximation of Pareto optimal front in multi-objective optimization.
        Computer methods in applied mechanics and engineering, 196(4-6), 879-893.

    Returns:
        Problem: The rocket injector design problem.
    """
    # Variables
    alpha = Variable(name="alpha", symbol="a", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0)

    deltaHA = Variable(
        name="deltaHA", symbol="DHA", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0
    )

    deltaOA = Variable(
        name="deltaOA", symbol="DOA", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0
    )

    OPTT = Variable(name="OPTT", symbol="OPTT", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0)

    # Objectives

    tfmax_eqn = """
                0.692+ 0.477 * a- 0.687 * DHA- 0.080 * DOA- 0.0650 * OPTT- 0.167 * a * a- 0.0129 * DHA * a
                + 0.0796 * DHA * DHA- 0.0634 * DOA * a- 0.0257 * DOA * DHA+ 0.0877 * DOA * DOA- 0.0521 * OPTT * a
                + 0.00156 * OPTT * DHA+ 0.00198 * OPTT * DOA+ 0.0184 * OPTT * OPTT
                """

    xccmax_eqn = """
                0.153- 0.322 * a+ 0.396 * DHA+ 0.424 * DOA+ 0.0226 * OPTT+ 0.175 * a * a
                + 0.0185 * DHA * a- 0.0701 * DHA * DHA- 0.251 * DOA * a+ 0.179 * DOA * DHA+ 0.0150 * DOA * DOA
                + 0.0134 * OPTT * a+ 0.0296 * OPTT * DHA+ 0.0752 * OPTT * DOA+ 0.0192 * OPTT * OPTT
                """

    ttmax_eqn = """
                0.370- 0.205 * a+ 0.0307 * DHA+ 0.108 * DOA+ 1.019 * OPTT- 0.135 * a * a+ 0.0141 * DHA * a
                + 0.0998 * DHA * DHA+ 0.208 * DOA * a- 0.0301 * DOA * DHA- 0.226 * DOA * DOA+ 0.353 * OPTT * a
                - 0.0497 * OPTT * DOA- 0.423 * OPTT * OPTT+ 0.202 * DHA * a * a- 0.281 * DOA * a * a
                - 0.342 * DHA * DHA * a- 0.245 * DHA * DHA * DOA+ 0.281 * DOA * DOA * DHA- 0.184 * OPTT * OPTT * a
                - 0.281 * DHA * a * DOA
                """

    tw4_eqn = """
                0.758 + 0.358 * a - 0.807 * DHA + 0.0925 * DOA - 0.0468 * OPTT
                - 0.172 * a * a + 0.0106 * DHA * a + 0.0697 * DHA * DHA
                - 0.146 * DOA * a - 0.0416 * DOA * DHA + 0.102 * DOA * DOA
                - 0.0694 * OPTT * a - 0.00503 * OPTT * DHA + 0.0151 * OPTT * DOA
                + 0.0173 * OPTT * OPTT
                """

    # The ideal and nadir values are estimates. If you get a better estimate, feel free to update them.
    tf_max = Objective(
        name="TF_max",
        symbol="TF_max",
        func=tfmax_eqn,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
        ideal=-0.008907,
        nadir=1.002000,
    )

    xcc_max = Objective(
        name="Xcc_max",
        symbol="Xcc_max",
        func=xccmax_eqn,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
        ideal=0.004883,
        nadir=1.075655,
    )

    tt_max = Objective(
        name="TT_max",
        symbol="TT_max",
        func=ttmax_eqn,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
        ideal=-0.419077,
        nadir=1.092842,
    )

    tw4 = Objective(
        name="TW4",
        symbol="TW4",
        func=tw4_eqn,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
        ideal=-0.013602,
        nadir=0.244688,
    )

    if original_version:  # NOQA:SIM108
        objectives = [tf_max, tw4, tt_max, xcc_max]
    else:
        objectives = [tf_max, tt_max, xcc_max]

    return Problem(
        name="Rocket Injector Design Problem",
        description=(
            "R. Vaidyanathan, K. Tucker, N. Papila, W. Shyy, CFD-Based Design Optimization For Single Element"
            " Rocket Injector, in: AIAA Aerospace Sciences Meeting, 2003, pp. 1-21."
        ),
        variables=[alpha, deltaHA, deltaOA, OPTT],
        objectives=objectives,
    )
