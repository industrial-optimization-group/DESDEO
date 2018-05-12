import pytest

from desdeo.method.NIMBUS import NIMBUS
from desdeo.optimization.OptimizationMethod import SciPyDE
from examples.NarulaWeistroffer import RiverPollution


@pytest.fixture(scope="function")
def method():
    return NIMBUS(RiverPollution(), SciPyDE)
