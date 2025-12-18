"""Export of the external module."""

from .core import ProviderParams
from .pymoo_provider import PymooProvider
from .runtime import get_registry, get_resolver, register_provider, supported_schemes

# register default providers here
register_provider("pymoo", PymooProvider())

__all__ = ["ProviderParams", "get_registry", "get_resolver", "register_provider", "supported_schemes"]
