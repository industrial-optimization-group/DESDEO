"""Imports from the external problems."""

from .core import ProviderRegistry, SimulatorResolver
from .pymoo_provider import PymooProvider

external_registry = ProviderRegistry()

# Register any providers here
external_registry.register("pymoo", PymooProvider())

external_resolver = SimulatorResolver(external_registry)

# TODO
# export locator URIs and endpoints as well
