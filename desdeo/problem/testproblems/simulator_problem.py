from pathlib import Path

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Simulator,
    Variable,
    VariableTypeEnum,
)

def simulator_problem(file_dir: str | Path):
    """A test problem with analytical, simulator and surrogate based objectives, constraints and extra functions.

    The problem uses two different simulator files. There are also objectives, constraints and extra fucntions that
    are surrogate based but it is assumed that the surrogate models are given when evaluating (while testing they
    are stored as temporary directories and files by pytest). There are also analytical functions to test utilizing
    PolarsEvaluator from the simulator evaluator.

    Args:
        file_dir (str | Path): path to the directory with the simulator files.
    """
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real),
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real),
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real),
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real),
    ]
    f1 = Objective(
        name="f_1",
        symbol="f_1",
        simulator_path=Path(f"{file_dir}/simulator_file.py"),
        objective_type=ObjectiveTypeEnum.simulator,
    )
    f2 = Objective(
        name="f_2", symbol="f_2", func="x_1 + x_2 + x_3", maximize=True, objective_type=ObjectiveTypeEnum.analytical
    )
    f3 = Objective(
        name="f_3",
        symbol="f_3",
        maximize=True,
        simulator_path=f"{file_dir}/simulator_file2.py",
        objective_type=ObjectiveTypeEnum.simulator,
    )
    f4 = Objective(
        name="f_4",
        symbol="f_4",
        simulator_path=f"{file_dir}/simulator_file.py",
        objective_type=ObjectiveTypeEnum.simulator,
    )
    f5 = Objective(name="f_5", symbol="f_5", objective_type=ObjectiveTypeEnum.surrogate)
    f6 = Objective(name="f_6", symbol="f_6", objective_type=ObjectiveTypeEnum.surrogate)
    g1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        simulator_path=f"{file_dir}/simulator_file2.py",
    )
    g2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func="-x_1 - x_2 - x_3",
    )
    g3 = Constraint(
        name="g_3",
        symbol="g_3",
        cons_type=ConstraintTypeEnum.LTE,
    )
    e1 = ExtraFunction(name="e_1", symbol="e_1", simulator_path=f"{file_dir}/simulator_file.py")
    e2 = ExtraFunction(name="e_2", symbol="e_2", func="x_1 * x_2 * x_3")
    e3 = ExtraFunction(
        name="e_3",
        symbol="e_3",
    )
    return Problem(
        name="Simulator problem",
        description="",
        variables=variables,
        objectives=[f1, f2, f3, f4, f5, f6],
        constraints=[g1, g2, g3],
        extra_funcs=[e1, e2, e3],
        simulators=[
            Simulator(
                name="s_1", symbol="s_1", file=Path(f"{file_dir}/simulator_file.py"), parameter_options={"delta": 0.5}
            ),
            Simulator(name="s_2", symbol="s_2", file=Path(f"{file_dir}/simulator_file2.py")),
        ],
    )
