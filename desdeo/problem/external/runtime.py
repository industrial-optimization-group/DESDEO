"""Runtime which owns a general ProviderResolver singleton and exposes functions to manage it."""

from .core import Provider, ProviderRegistry, ProviderResolver

_registry = ProviderRegistry()
_resolver = ProviderResolver(_registry)

# if uri's of other type than 'desdeo://...' are to be supported, update this list
supported_schemes = ["desdeo"]


def get_registry() -> ProviderRegistry:
    """Get the runtime registry."""
    return _registry


def get_resolver() -> ProviderResolver:
    """Get the runtime provider resolver."""
    return _resolver


def register_provider(name: str, provider: Provider, *, overwrite: bool = False, clear_cache: bool = True) -> None:
    """Register a provider to the current runtime resolver.

    Args:
        name (str): name of the provider.
        provider (Provider): the instance of the provider.
        overwrite (bool, optional): should an existing provider with the same
            name be overwritten, if it already exits? Defaults to False.
        clear_cache (bool, optional): should the resolver's cache be cleared? Defaults to True.

    Raises:
        KeyError: if overwrite is 'False' and a provider with the given `name`
            already exists in the register of the resolver.
    """
    reg = get_registry()

    if reg.has(name) and not overwrite:
        raise KeyError(f"Provider {name!r} already registered")

    reg.register(name, provider)

    if clear_cache:
        get_resolver().clear_caches()
