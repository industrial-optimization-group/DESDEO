import pytest

from pyDESDEO.method.NIMBUS import NIMBUS
from pyDESDEO.examples.NarulaWeistroffer import NaurulaWeistroffer
from pyDESDEO.optimization.OptimizationMethod import SciPyDE


@pytest.fixture(scope = "function")
def method():
    return  NIMBUS(NaurulaWeistroffer(), SciPyDE)
