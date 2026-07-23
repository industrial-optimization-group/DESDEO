import numpy as np
import pytest
from desdeo.problem.testproblems import river_pollution_problem
from desdeo.tools import PyomoIpoptSolver, payoff_table_method
from desdeo.adm import ADMAfsar, ADMChen


@pytest.fixture
def problem():
    np.random.seed(42)
    prob = river_pollution_problem(five_objective_variant=False)
    ideal, nadir = payoff_table_method(prob, solver=PyomoIpoptSolver)
    return prob.update_ideal_and_nadir(ideal, nadir)


@pytest.fixture
def front():
    return np.array([
        [-6.34, -3.44, -7.50, 0.00],
        [-6.10, -3.20, -5.00, -3.50],
        [-5.80, -3.10, -3.00, -6.00],
        [-5.50, -2.95, -1.00, -8.00],
        [-4.75, -2.85, -0.32, -9.71],
    ])


def test_admafsar_creation(problem):
    adm = ADMAfsar(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        number_of_vectors=10,
    )
    assert adm.reference_vectors.shape[1] == len(problem.objectives)
    assert adm.preference is not None
    assert adm.preference.shape[0] == len(problem.objectives)


def test_admafsar_full_iteration_cycle(problem, front):
    adm = ADMAfsar(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        number_of_vectors=10,
    )
    seen_phases = set()
    for i in range(adm.max_iterations):
        assert adm.has_next() is True
        phase = "learning" if adm.iteration_counter < adm.it_learning_phase else "decision"
        seen_phases.add(phase)
        pref = adm.get_next_preference(front, preference_type="reference_point")
        assert pref is not None
        assert not np.any(np.isnan(np.asarray(pref, dtype=float)))

    assert "learning" in seen_phases
    assert "decision" in seen_phases
    assert adm.has_next() is False


def test_admafsar_public_vector_accessors(problem, front):
    adm = ADMAfsar(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        number_of_vectors=10,
    )
    assert adm.reference_vectors_ is not None
    assert adm.assigned_vectors_ is None

    adm.get_next_preference(front, preference_type="reference_point")

    assert adm.assigned_vectors_ is not None
    assert len(adm.assigned_vectors_) > 0
    assert np.all(adm.assigned_vectors_ >= 0)
    assert np.all(adm.assigned_vectors_ < adm.reference_vectors_.shape[0])


def test_admafsar_no_redundant_payoff_table_call(problem, monkeypatch):
    call_count = {"n": 0}
    import desdeo.adm.adm_afsar as admafsar_module

    original = admafsar_module.payoff_table_method

    def counting_payoff(*args, **kwargs):
        call_count["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(admafsar_module, "payoff_table_method", counting_payoff)

    ADMAfsar(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        number_of_vectors=10,
    )
    assert call_count["n"] == 1


def test_admchen_creation(problem, front):
    adm_chen = ADMChen(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        pareto_front=front,
    )
    assert adm_chen.preference is not None
    assert adm_chen.UF_max is not None
    assert adm_chen.UF_opt is not None


def test_admchen_full_iteration_cycle(problem, front):
    adm_chen = ADMChen(
        problem=problem,
        it_learning_phase=3,
        it_decision_phase=2,
        pareto_front=front,
    )
    for _ in range(adm_chen.max_iterations - 1):
        assert adm_chen.has_next() is True
        pref = adm_chen.get_next_preference(front)
        assert pref is not None

    assert adm_chen.has_next() is False