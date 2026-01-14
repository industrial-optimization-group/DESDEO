"""Export of the external module."""

from .core import ProviderParams
from .pymoo_provider import PymooProblemParams, PymooProvider, create_pymoo_problem
from .runtime import get_registry, get_resolver, register_provider, supported_schemes

# register default providers here
register_provider("pymoo", PymooProvider())

__all__ = [
    "ProviderParams",
    "PymooProblemParams",
    "create_pymoo_problem",
    "get_registry",
    "get_resolver",
    "register_provider",
    "supported_schemes",
]
