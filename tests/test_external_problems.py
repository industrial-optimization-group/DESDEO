"""Test related to the external problems."""

import pytest

from desdeo.problem.external.core import ProviderRegistry, SimulatorResolver
from desdeo.problem.external.pymoo_provider import (
    PymooParams,
    PymooProvider,
    _get_cached_pymoo_problem,
    create_pymoo_problem,
)


@pytest.mark.external
def test_pymoo_proivder():
    """Test the basic operation of the Pymoo problem provider."""
    registry = ProviderRegistry()

    registry.register("pymoo", PymooProvider())

    resolver = SimulatorResolver(registry)

    locator = "desdeo://external/pymoo/evaluate"
    # params = {"name": "dtlz2", "n_var": 12, "n_obj": 3, "minus": False}
    # X = [[0.1] * 12, [0.2] * 12, [0.5] * 12]
    params = PymooParams(name="truss2d")
    X = [[1.0] * 3, [2.0] * 3]

    for _ in range(10):
        out = resolver.evaluate(locator, params, X)

    print()


@pytest.mark.external
def test_pymoo_construct_problem():
    """Test that the pymoo provider can be used to construct a DESDEO Problem."""
    params = PymooParams(name="dtlz2", n_var=12, n_obj=3)

    problem = create_pymoo_problem(params)

    print()
