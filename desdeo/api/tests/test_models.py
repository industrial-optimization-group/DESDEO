"""Tests related to the SQLModels."""

from sqlmodel import Session, select

from desdeo.api.models import (
    ArchiveEntryBase,
    ArchiveEntryDB,
    Bounds,
    ConstantDB,
    ConstraintDB,
    DiscreteRepresentationDB,
    ExtraFunctionDB,
    InteractiveSessionDB,
    ObjectiveDB,
    PreferenceDB,
    ProblemDB,
    ReferencePoint,
    RPMState,
    ScalarizationFunctionDB,
    SimulatorDB,
    StateDB,
    TensorConstantDB,
    TensorVariableDB,
    User,
    VariableDB,
)
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    ScalarizationFunction,
    Simulator,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.testproblems import (
    binh_and_korn,
    dtlz2,
    momip_ti2,
    momip_ti7,
    nimbus_test_problem,
    pareto_navigator_test_problem,
    re21,
    re22,
    re23,
    re24,
    river_pollution_problem,
    river_pollution_problem_discrete,
    simple_data_problem,
    simple_knapsack,
    simple_knapsack_vectors,
    simple_linear_test_problem,
    simple_scenario_test_problem,
    simple_test_problem,
    spanish_sustainability_problem,
    zdt1,
)
from desdeo.tools import available_solvers


def compare_models(
    model_1,
    model_2,
    unordered_fields=None,
) -> bool:
    """Compares two Pydantic models.

    Args:
        model_1 (Any): Pydantic model 1.
        model_2 (Any): Pydantic model 2.
        unordered_fields (list[str]): field names that are unordered and should be compared for
            having the same contents.

    Returns:
        bool: Whether the two models have identical contents.
    """
    if unordered_fields is None:
        unordered_fields = [
            "variables",
            "constants",
            "objectives",
            "constraints",
            "extra_funcs",
            "simulators",
            "scenario_keys",
        ]

    dict_1 = model_1.model_dump()
    dict_2 = model_2.model_dump()

    for field in unordered_fields:
        if field in dict_1 and field in dict_2 and isinstance(dict_1[field], list) and isinstance(dict_2[field], list):
            if len(dict_1[field]) != len(dict_2[field]):
                return False

            for key_1, key_2 in zip(dict_1, dict_2, strict=True):
                if key_1 not in dict_2 or key_2 not in dict_1:
                    return False

                if dict_1[key_1] != dict_1[key_2]:
                    return False

                if dict_2[key_1] != dict_2[key_2]:
                    return False

            del dict_1[field], dict_2[field]

    return dict_1 == dict_2


def test_tensor_constant(session_and_user: dict[str, Session | list[User]]):
    """Test that a tensor constant can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    t_tensor = TensorConstant(name="tensor", symbol="T", shape=[2, 2], values=[[1, 2], [3, 4]])
    t_tensor_dump = t_tensor.model_dump()
    t_tensor_dump["problem_id"] = 1

    db_tensor = TensorConstantDB.model_validate(t_tensor_dump)

    session.add(db_tensor)
    session.commit()

    statement = select(TensorConstantDB).where(TensorConstantDB.problem_id == 1)
    from_db_tensor = session.exec(statement).first()

    # check that original added TensorConstant and fetched match
    assert db_tensor == from_db_tensor

    from_db_tensor_dump = from_db_tensor.model_dump()
    t_tensor_validated = TensorConstant.model_validate(from_db_tensor_dump)

    assert t_tensor_validated == t_tensor


def test_constant(session_and_user: dict[str, Session | list[User]]):
    """Test that a scalar constant can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    constant = Constant(name="constant", symbol="c", value=69.420)
    constant_dump = constant.model_dump()
    constant_dump["problem_id"] = 1

    db_constant = ConstantDB.model_validate(constant_dump)

    session.add(db_constant)
    session.commit()

    statement = select(ConstantDB).where(ConstantDB.problem_id == 1)
    from_db_constant = session.exec(statement).first()

    assert db_constant == from_db_constant

    from_db_constant_dump = from_db_constant.model_dump()
    constant_validated = Constant.model_validate(from_db_constant_dump)

    assert constant_validated == constant


def test_variable(session_and_user: dict[str, Session | list[User]]):
    """Test that a scalar variable can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    variable = Variable(
        name="test variable",
        symbol="x_1",
        initial_value=69,
        lowerbound=42,
        upperbound=420,
        variable_type=VariableTypeEnum.integer,
    )

    variable_dump = variable.model_dump()
    variable_dump["problem_id"] = 1

    db_variable = VariableDB.model_validate(variable_dump)

    session.add(db_variable)
    session.commit()
    session.refresh(db_variable)

    from_db_variable = session.get(VariableDB, db_variable.id)

    assert db_variable == from_db_variable

    from_db_variable_dump = from_db_variable.model_dump()
    variable_validated = Variable.model_validate(from_db_variable_dump)

    assert variable_validated == variable


def test_tensor_variable(session_and_user: dict[str, Session | list[User]]):
    """Test that a tensor variable can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    t_variable = TensorVariable(
        name="test variable",
        symbol="X",
        shape=[2, 2],
        initial_values=[[1, 2], [3, 4]],
        lowerbounds=[[0, 1], [1, 0]],
        upperbounds=[[99, 89], [88, 77]],
        variable_type=VariableTypeEnum.integer,
    )

    t_variable_dump = t_variable.model_dump()
    t_variable_dump["problem_id"] = 69

    db_t_variable = TensorVariableDB.model_validate(t_variable_dump)

    session.add(db_t_variable)
    session.commit()
    session.refresh(db_t_variable)

    from_db_t_variable = session.get(TensorVariableDB, db_t_variable.id)

    assert db_t_variable == from_db_t_variable

    from_db_t_variable_dump = from_db_t_variable.model_dump()
    t_variable_validated = TensorVariable.model_validate(from_db_t_variable_dump)

    assert t_variable_validated == t_variable


def test_objective(session_and_user: dict[str, Session | list[User]]):
    """Test that an objective can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    objective = Objective(
        name="Test Objective",
        symbol="f_1",
        func="x_1 + x_2 + Sin(y)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=10.5,
        nadir=20.0,
        maximize=False,
        scenario_keys=["s_1", "s_2"],
        unit="m",
        is_convex=False,
        is_linear=True,
        is_twice_differentiable=True,
        simulator_path="/dev/null",
        surrogates=["/var/log", "/dev/sda/sda1"],
    )

    objective_dump = objective.model_dump()
    objective_dump["problem_id"] = 420  # yes

    db_objective = ObjectiveDB.model_validate(objective_dump)

    session.add(db_objective)
    session.commit()
    session.refresh(db_objective)

    from_db_objective = session.get(ObjectiveDB, db_objective.id)

    assert db_objective == from_db_objective

    from_db_objective_dump = from_db_objective.model_dump()
    objective_validated = Objective.model_validate(from_db_objective_dump)

    assert objective_validated == objective


def test_constraint(session_and_user: dict[str, Session | list[User]]):
    """Test that an constraint can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    constraint = Constraint(
        name="Test Constraint",
        symbol="g_1",
        func="x_1 + x_1 + x_1 - 10",
        cons_type=ConstraintTypeEnum.LTE,
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=False,
        scenario_keys=["Abloy", "MasterLock", "MasterLockToOpenMasterLock"],
        simulator_path="/dev/null/aaaaaaaaaa",
        surrogates=["/var/log", "/dev/sda/sda1/no"],
    )

    constraint_dump = constraint.model_dump()
    constraint_dump["problem_id"] = 72

    db_constraint = ConstraintDB.model_validate(constraint_dump)

    session.add(db_constraint)
    session.commit()
    session.refresh(db_constraint)

    from_db_constraint = session.get(ConstraintDB, db_constraint.id)

    assert db_constraint == from_db_constraint

    from_db_constraint_dump = from_db_constraint.model_dump()
    constraint_validated = Constraint.model_validate(from_db_constraint_dump)

    assert constraint_validated == constraint


def test_scalarization_function(session_and_user: dict[str, Session | list[User]]):
    """Test that a scalarization function can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    scalarization = ScalarizationFunction(
        name="Test ScalarizationFunction",
        symbol="s_1",
        func="x_1 + x_1 + x_1 - 10 - 99999 + Sin(y_3)",
        is_convex=True,
        is_linear=True,
        is_twice_differentiable=False,
        scenario_keys=["Abloy", "MasterLock", "MasterLockToOpenMasterLock", "MyHandsHurt"],
    )

    scalarization_dump = scalarization.model_dump()
    scalarization_dump["problem_id"] = 2

    db_scalarization = ScalarizationFunctionDB.model_validate(scalarization_dump)

    session.add(db_scalarization)
    session.commit()
    session.refresh(db_scalarization)

    from_db_scalarization = session.get(ScalarizationFunctionDB, db_scalarization.id)

    assert db_scalarization == from_db_scalarization

    from_db_scalarization_dump = from_db_scalarization.model_dump()
    scalarization_validated = ScalarizationFunction.model_validate(from_db_scalarization_dump)

    assert scalarization_validated == scalarization


def test_extra_function(session_and_user: dict[str, Session | list[User]]):
    """Test that an extra function can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    extra = ExtraFunction(
        name="Test ExtraFunction",
        symbol="extra_1",
        func="x_1 + x_2 + x_9000 - 10 - 99999 + Cos(y_3)",
        is_convex=False,
        is_linear=False,
        is_twice_differentiable=True,
        scenario_keys=["Abloy", "MasterLock", "MasterLockToOpenMasterLock", "MyHandsHurt", "RunningOutOfIdeas"],
    )

    extra_dump = extra.model_dump()
    extra_dump["problem_id"] = 5

    db_extra = ExtraFunctionDB.model_validate(extra_dump)

    session.add(db_extra)
    session.commit()
    session.refresh(db_extra)

    from_db_extra = session.get(ExtraFunctionDB, db_extra.id)

    assert db_extra == from_db_extra

    from_db_extra_dump = from_db_extra.model_dump()
    extra_validated = ExtraFunction.model_validate(from_db_extra_dump)

    assert extra_validated == extra


def test_discrete_representation(session_and_user: dict[str, Session | list[User]]):
    """Test that a DiscreteRepresentation can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    discrete = DiscreteRepresentation(
        variable_values={"x_1": [1, 2, 3, 4, 5], "x_2": [6, 7, 8, 9, 10]},
        objective_values={"f_1": [0.5, 1.0, 2.0, 3.5, 9], "f_2": [-1, -2, -3, -4, -5]},
        non_dominated=True,
    )

    discrete_dump = discrete.model_dump()
    discrete_dump["problem_id"] = 3

    db_discrete = DiscreteRepresentationDB.model_validate(discrete_dump)

    session.add(db_discrete)
    session.commit()
    session.refresh(db_discrete)

    from_db_discrete = session.get(DiscreteRepresentationDB, db_discrete.id)

    assert db_discrete == from_db_discrete

    from_db_discrete_dump = from_db_discrete.model_dump()
    discrete_validated = DiscreteRepresentation.model_validate(from_db_discrete_dump)

    assert discrete_validated == discrete


def test_simulator(session_and_user: dict[str, Session | list[User]]):
    """Test that a Simulator can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_user["session"]

    simulator = Simulator(
        file="/my/favorite/simulator.exe",
        name="simulator",
        symbol="simu",
        parameter_options={"param1": 69, "nice": True},
    )

    simulator_dump = simulator.model_dump()
    simulator_dump["problem_id"] = 2

    db_simulator = SimulatorDB.model_validate(simulator_dump)

    session.add(db_simulator)
    session.commit()
    session.refresh(db_simulator)

    from_db_simulator = session.get(SimulatorDB, db_simulator.id)

    assert db_simulator == from_db_simulator

    from_db_simulator_dump = from_db_simulator.model_dump()
    simulator_validated = Simulator.model_validate(from_db_simulator_dump)

    assert simulator_validated == simulator


def test_from_pydantic(session_and_user: dict[str, Session | list[User]]):
    """Test that a problem can be added and fetched from the database correctly."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    problem_binh = binh_and_korn()

    problemdb = ProblemDB.from_problem(problem_binh, user=user)
    session.add(problemdb)
    session.commit()
    session.refresh(problemdb)

    from_db_problem = session.get(ProblemDB, problemdb.id)

    assert compare_models(problemdb, from_db_problem)


def test_from_problem_to_d_and_back(session_and_user: dict[str, Session | list[User]]):
    """Test that Problem converts to ProblemDB and back."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    problems = [
        binh_and_korn(),
        river_pollution_problem(),
        simple_knapsack(),
        simple_data_problem(),
        simple_scenario_test_problem(),
        re24(),
        simple_knapsack_vectors(),
        spanish_sustainability_problem(),
        zdt1(10),
        dtlz2(5, 3),
        momip_ti2(),
        momip_ti7(),
        nimbus_test_problem(),
        pareto_navigator_test_problem(),
        river_pollution_problem_discrete(),
        simple_test_problem(),
        simple_linear_test_problem(),
        re21(),
        re22(),
        re23(),
    ]

    for problem in problems:
        # convert to SQLModel
        problem_db = ProblemDB.from_problem(problem, user=user)

        session.add(problem_db)
        session.commit()
        session.refresh(problem_db)

        from_db = session.get(ProblemDB, problem_db.id)

        # Back to pure pydantic
        problem_db = Problem.from_problemdb(from_db)

        # check that problems are equal
        assert compare_models(problem, problem_db)


def test_archive_entry(session_and_user: dict[str, Session | list[User]]):
    """Test that the archive works as intended."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    problem = dtlz2(n_variables=5, n_objectives=3)
    problem_db = ProblemDB.from_problem(problem, user)

    session.add(problem_db)
    session.commit()
    session.refresh(problem_db)

    variable_values = {"x_1": 0.3, "x_2": 0.8, "x_3": 0.1, "x_4": 0.6, "x_5": 0.9}
    objective_values = {"f_1": 1.2, "f_2": 0.9, "f_3": 1.5}
    constraint_values = {"g_1": 0.1}
    extra_func_values = {"extra_1": 5000, "extra_2": 600000}

    archive_entry = ArchiveEntryBase(variable_values=variable_values, objective_values=objective_values)

    archive_entry_db = ArchiveEntryDB.model_validate(
        archive_entry,
        update={
            "user_id": user.id,
            "problem_id": problem_db.id,
            "constraint_values": constraint_values,
            "extra_func_values": extra_func_values,
        },
    )

    session.add(archive_entry_db)
    session.commit()
    session.refresh(archive_entry_db)

    from_db = session.get(ArchiveEntryDB, archive_entry_db.id)

    assert from_db.user_id == user.id
    assert from_db.problem_id == problem_db.id
    assert from_db == user.archive[0]
    assert compare_models(from_db.problem, problem_db)
    assert from_db.variable_values == variable_values
    assert from_db.objective_values == objective_values
    assert from_db.constraint_values == constraint_values
    assert from_db.extra_func_values == extra_func_values


def test_preference_models(session_and_user: dict[str, Session | list[User]]):
    """Test that the archive works as intended."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)

    session.add(problem)
    session.commit()
    session.refresh(problem)

    aspiration_levels = {"f_1": 0.1, "f_2": 5, "f_3": -3.1}
    lower_bounds = {"f_1": -4.1, "f_2": 0, "f_3": 2.2}
    upper_bounds = {"f_1": 2.1, "f_2": 0.1, "f_3": 12.2}

    reference_point = ReferencePoint(aspiration_levels=aspiration_levels)
    bounds = Bounds(lower_bounds=lower_bounds, upper_bounds=upper_bounds)

    reference_point_db = PreferenceDB(user_id=user.id, problem_id=problem.id, preference=reference_point)
    bounds_db = PreferenceDB(user_id=user.id, problem_id=problem.id, preference=bounds)

    session.add(reference_point_db)
    session.add(bounds_db)
    session.commit()
    session.refresh(reference_point_db)
    session.refresh(bounds_db)

    from_db_ref_point = session.get(PreferenceDB, reference_point_db.id)
    from_db_bounds = session.get(PreferenceDB, bounds_db.id)

    assert from_db_ref_point.preference.aspiration_levels == aspiration_levels
    assert from_db_bounds.preference.lower_bounds == lower_bounds
    assert from_db_bounds.preference.upper_bounds == upper_bounds

    assert from_db_ref_point.problem == problem
    assert from_db_ref_point.problem == problem
    assert from_db_bounds.problem == problem

    assert from_db_bounds.user == user
    assert from_db_ref_point.user == user

    assert from_db_bounds.solutions == []
    assert from_db_ref_point.solutions == []


def test_rpm_state(session_and_user: dict[str, Session | list[User]]):
    """Test the RPM state that it works correctly."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_db = user.problems[0]

    # create interactive session
    isession = InteractiveSessionDB(user_id=user.id)

    session.add(isession)
    session.commit()
    session.refresh(isession)

    # use the reference point method
    asp_levels_1 = {"f_1": 0.4, "f_2": 0.8, "f_3": 0.6}

    problem = Problem.from_problemdb(problem_db)

    scalarization_options = None
    solver = "pyomo_bonmin"
    solver_options = None

    results = rpm_solve_solutions(
        problem,
        asp_levels_1,
        scalarization_options=scalarization_options,
        solver=available_solvers[solver],
        solver_options=solver_options,
    )

    # create preferences

    rp_1 = ReferencePoint(aspiration_levels=asp_levels_1)
    preferences = PreferenceDB(user_id=user.id, problem_id=problem_db.id, preference=rp_1)

    session.add(preferences)
    session.commit()
    session.refresh(preferences)

    # create state

    rpm_state = RPMState(
        scalarization_options=scalarization_options,
        solver=solver,
        solver_options=solver_options,
        solver_results=results,
    )

    state_1 = StateDB(
        problem_id=problem_db.id, preference_id=preferences.id, session_id=isession.id, parent_id=None, state=rpm_state
    )

    session.add(state_1)
    session.commit()
    session.refresh(state_1)

    asp_levels_2 = {"f_1": 0.6, "f_2": 0.4, "f_3": 0.5}

    problem = Problem.from_problemdb(problem_db)

    scalarization_options = None
    solver = "pyomo_bonmin"
    solver_options = None

    results = rpm_solve_solutions(
        problem,
        asp_levels_2,
        scalarization_options=scalarization_options,
        solver=available_solvers[solver],
        solver_options=solver_options,
    )

    # create preferences

    rp_2 = ReferencePoint(aspiration_levels=asp_levels_2)
    preferences = PreferenceDB(user_id=user.id, problem_id=problem_db.id, preference=rp_2)

    session.add(preferences)
    session.commit()
    session.refresh(preferences)

    # create state

    rpm_state = RPMState(
        scalarization_options=scalarization_options,
        solver=solver,
        solver_options=solver_options,
        solver_results=results,
    )

    state_2 = StateDB(
        problem_id=problem_db.id,
        preference_id=preferences.id,
        session_id=isession.id,
        parent_id=state_1.id,
        state=rpm_state,
    )

    session.add(state_2)
    session.commit()
    session.refresh(state_2)

    assert state_1.parent is None
    assert state_2.parent == state_1
    assert len(state_1.children) == 1
    assert state_1.children[0] == state_2

    assert state_1.preference.preference == rp_1
    assert state_2.preference.preference == rp_2

    assert state_2.problem == problem_db
    assert state_2.session.user == user

    assert state_2.children == []
    assert state_2.parent.problem == problem_db
    assert state_2.parent.session.user == user
