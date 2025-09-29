PI = 3.14159265358979323846

from desdeo.problem.schema import (
    Constant,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

## Helper func
def U(z: float):
    return 4.0*z*(1.0 - z)

## Helper funcs to return string representations
def clamp01_str(v: float):
    return f"(Max(0, Min(1, {v})))"

def bowl_str(z: str, a: str, invD: str) -> str:
    tmp : str = f"({z} - {a})*{invD}"
    return f"({tmp}*{tmp})"
    #return f"{clamp01_str(f"{tmp}*{tmp}")}"

def U_str(z: str) -> str:
    tmp: str = f"(4*{z}*(1.0 - {z}))"
    return f"({tmp}*{tmp})"

def ripple_str(t: str) -> str:
    tmp: str = f"Sin({PI} * {t})"
    return f"({tmp}*{tmp})"

# Objective function string representations
def f0_str() -> str:
    yliq: str = "(0.5*x5 + 0.3*x4 + 0.2*x3)"
    v: str = f"(0.4 * {bowl_str("x1", "T1", "INV_D1")}) + " \
        f"(0.4 * {bowl_str(yliq, "Y_LIQ_STAR", "INV_D_YLIQ")}) + " \
        f" (0.2 * {ripple_str("((x1 + x6) - (T1 + T6))")})"
    return f"14*({v})"

def f1_str() -> str:
    sbar: str = "((x2 + 0.5*x3)/1.5)"
    w25: str = f"({U_str("x2")}*{U_str("x5")})"
    d25: str = f"(({w25} - W25_STAR)*INV_DW25)"
    v: str = f"(0.4*{bowl_str("x2", "T2", "INV_D2")}) + "\
        f"(0.3*{ripple_str(f"{sbar} - SBAR_STAR")}) +"\
        f"(0.3*{d25}*{d25})"
    return f"14*({v})"

def f2_str() -> str:
    v: str = f"(0.35*{bowl_str("x6", "T6", "INV_D6")}) + "\
        f"(0.25*{bowl_str("x4", "T4", "INV_D4")}) + "\
        f"(0.4*{ripple_str("((x6 - 0.5*x4) - (T6 - 0.5*T4))")})"
    return f"14*({v})"

def f3_str() -> str:
    w35: str = f"({U_str("x3")}*{U_str("x5")})"
    d35: str = f"(({w35} - W35_STAR) * INV_DW35)"
    v: str = f"(0.3*{bowl_str("x3", "T3", "INV_D3")}) + "\
        f"(0.3*{bowl_str("x5", "T5", "INV_D5")}) + "\
        f"(0.4*({d35}*{d35}))"
    return f"14*({v})"

def f4_str() -> str:
    v: str = f"(0.25*{bowl_str("x2", "T2", "INV_D2")}) + "\
        f"(0.25*{bowl_str("x3", "T3", "INV_D3")}) + "\
        f"(0.20*{ripple_str("(x4 - T4)")}) + "\
        f"(0.30*{ripple_str("((x2 - x5) - (T2 - T5))")})"
    return f"14*({v})"

## The cake problem
def best_cake_problem() -> Problem:
    r"""
    Defines the best cake problem.
    """
    variable_inits = [
        ("Flour", 0.70),
        ("Sugar", 0.10),
        ("Butter", 0.40),
        ("Eggs", 0.50),
        ("Milk", 0.20),
        ("Baking powder", 0.80)
    ]
    variables = [
        Variable(
            name=var[0],
            symbol=f"x{i + 1}",
            variable_type=VariableTypeEnum.real,
            lowerbound=0.0,
            upperbound=1.0,
            initial_value=var[1],
        )
        for i, var in enumerate(variable_inits)
    ]

    constants_init = [
        ("T1", 0.60),
        ("T2", 0.35),
        ("T3", 0.25),
        ("T4", 0.30),
        ("T5", 0.35),
        ("T6", 0.40),

        ("INV_D1", 1.0/0.60),
        ("INV_D2", 1.0/0.65),
        ("INV_D3", 1.0/0.75),
        ("INV_D4", 1.0/0.70),
        ("INV_D5", 1.0/0.65),
        ("INV_D6", 1.0/0.60),

        ("Y_LIQ_STAR", 0.5*0.35 + 0.3*0.30 + 0.2*0.25),
        ("INV_D_YLIQ", 1.0/0.685),
        ("SBAR_STAR", (0.35 + 0.5*0.25)/1.5),

        ("W25_STAR", U(0.35)*U(0.35)),
        ("INV_DW25", 1.0/0.8281),
        ("W35_STAR", U(0.25)*U(0.35)),
        ("INV_DW35", 1.0/0.6825),
    ]

    constants = [
        Constant(
            name=const[0],
            symbol=const[0],
            value=const[1]
        )
        for const in constants_init
    ]

    objectives = [
        Objective(
            name="Dry/crumb error",
            symbol="dry_crumb",
            func=f0_str(),
            ideal=0.0,
            nadir=14.0,
            objective_type=ObjectiveTypeEnum.analytical,
            is_twice_differentiable=True # right?
        ),
        Objective(
            name="Sweetness/texture off-target",
            symbol="sweet_texture",
            func=f1_str(),
            ideal=0.0,
            nadir=14.0,
            objective_type=ObjectiveTypeEnum.analytical,
            is_twice_differentiable=True
        ),
        Objective(
            name="Rise/collapse risk",
            symbol="rise_collapse",
            func=f2_str(),
            ideal=0.0,
            nadir=14.0,
            objective_type=ObjectiveTypeEnum.analytical,
            is_twice_differentiable=True
        ),
        Objective(
            name="Moistness/grease imbalance",
            symbol="moistness_grease",
            func=f3_str(),
            ideal=0.0,
            nadir=14.0,
            objective_type=ObjectiveTypeEnum.analytical,
            is_twice_differentiable=True
        ),
        Objective(
            name="Browning/burn risk",
            symbol="browning_burn",
            func=f4_str(),
            ideal=0.0,
            nadir=14.0,
            objective_type=ObjectiveTypeEnum.analytical,
            is_twice_differentiable=True
        ),
    ]
    
    return Problem(
        name="Cake problem",
        description="Try to find the most delicious cake!",
        constants=constants,
        variables=variables,
        objectives=objectives
    )

def into_db(uname: str):
    """ 
    An utility function to add the cake problem 
    to database under a certain user
    """
    from desdeo.api.db import get_session
    from desdeo.api.models import ProblemDB, User
    from sqlmodel import select

    problem = best_cake_problem()

    session = next(get_session())
    user = session.exec(select(User).where(User.username == uname)).first()
    if user is None:
        print(f"No user with name {uname}!")
        return

    problem_db = ProblemDB.from_problem(problem_instance=problem, user=user)

    session.add(problem_db)
    session.commit()