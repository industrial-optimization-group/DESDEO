"""Implements a interface to interface into external (test) problem suites."""

import json
from typing import Any, Literal, Protocol
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field

from desdeo.problem import ConstraintTypeEnum, VariableType, VariableTypeEnum

Operation = Literal["info", "evaluate"]
Scheme = Literal["desdeo", "http"]


class ExternalProblemInfo(BaseModel):
    """A model to represent problem information of problems, which are not native to DESDEO."""

    name: str = Field(description="Name of the problem")
    description: str | None = Field(description="Description of the problem. Default to 'None'.", default=None)
    variable_symbols: list[str] = Field(description="The symbols of the variables.")
    variable_names: dict[str, str] | None = Field(
        description=(
            "The names of the variables. It is expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case the symbols are used."
        )
    )
    variable_type: dict[str, VariableTypeEnum] | None = Field(
        description=(
            "The type of each variable (real, integer, binary). It is "
            "expected that the keys are the same as the provided symbols. If 'None', "
            "the type 'real' is assumed for all variables. Defaults to 'None'."
        )
    )
    variable_lower_bounds: dict[str, VariableType | None] | None = Field(
        description=(
            "The lower bound of each variable. It is "
            "expected that the keys are the same as the provided symbols. If 'None', "
            "the value is None, no bounds are assumed for all lower bounds. variables. Defaults to 'None'."
        )
    )
    variable_upper_bounds: dict[str, VariableType | None] | None = Field(
        description=(
            "The upper bound of each variable. It is "
            "expected that the keys are the same as the provided symbols. If 'None', "
            "the value is None, no bounds are assumed for all upper bounds. variables. Defaults to 'None'."
        )
    )
    objective_symbols: list[str] = Field(description="The names of the objective functions.")
    objective_names: dict[str, str] | None = Field(
        description=(
            "The names of the objectives. It is expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case the symbols are used."
        )
    )
    objective_maximize: dict[str, bool] | None = Field(
        description=(
            "Whether objective are to be maximized. It is "
            "expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case minimization is assumed."
        )
    )
    ideal_point: dict[str, float] | None = Field(
        description=(
            "The ideal point of the problem. The keys should match those of the objective functions. "
            "Defaults to 'None'."
        ),
        default=None,
    )
    nadir_point: dict[str, float] | None = Field(
        description=(
            "The nadir point of the problem. The keys should match those of the objective functions. "
            "Defaults to 'None'."
        ),
        default=None,
    )
    constraint_symbols: list[str] | None = Field(
        description=(
            "The symbols of constraints. If 'None', no constraints are defined for the problem. Defaults to None."
        )
    )
    constraint_names: dict[str, str] | None = Field(
        description=(
            "The names of the constraints. It is expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case the symbols are used."
        )
    )
    constraint_types: dict[str, ConstraintTypeEnum] | None = Field(
        description=(
            "The types (LTE, EQ...) of the constraints. It is expected that the "
            "keys are the same as the provided symbols. Defaults to 'None', in "
            "which case no symbols are assumed to be defined."
        )
    )


class ExternalProblemParams(BaseModel):
    """A model to represent parameters that can be used to generate problems, which are not native to DESDEO."""


class ProviderParams(BaseModel):
    """A model to represent parameters that external libraries can use to build problem."""


class Locator(BaseModel):
    """A model to represent a locator, i.e., a URI."""

    scheme: Scheme = Field(description="The source of the problem.")
    provider: str | None = Field(description="The provider of the operation. Defaults to 'None'.", default=None)
    op: Operation | None = Field(description="The associated operator. Defaults to 'None'.", default=None)
    raw: str = Field(description="The raw uri.")

    # for http
    http_url: str | None = Field(description="Uri for web-access. Defaults to 'None'.", default=None)


class LocatorParseError(ValueError):
    """Raised when errors emerge parsing a locator."""


def parse_locator(uri: str) -> Locator:
    """Parses a string representing a uri into a Locator model.

    Args:
        uri (str): a string containing a uri. Should follow the format 'scheme://provider/operation'.

    Raises:
        LocatorParsesError: when parsing the uri goes wrong for one reason or another.

    Returns:
        Locator: a locator with the information parsed from the uri.
    """
    p = urlparse(uri)
    expected_segments = 2

    if p.scheme in ("http", "https"):
        segments = [s for s in p.path.split("/") if s]
        if len(segments) == expected_segments:
            provider, op = segments
        else:
            raise LocatorParseError(f"Invalid path; expected 2 segments in {uri!r}")

        return Locator(
            scheme="http",
            op=None,
            provider=None,
            raw=uri,
            http_url=uri,
        )

    if p.scheme != "desdeo":
        raise LocatorParseError(f"Unsupported scheme: {p.scheme!r} in {uri!r}")

    segments = [s for s in p.path.split("/") if s]
    if len(segments) == expected_segments:
        provider, op = segments
    else:
        raise LocatorParseError(f"Invalid path; expected 2 segments in {uri!r}")

    if op not in ("info", "evaluate"):
        raise LocatorParseError(f"Unsupported operation {op!r} in {uri!r}")

    if not provider or not (provider[0].isalpha() and all(c.isalnum() or c in "_-" for c in provider)):
        raise LocatorParseError(f"Invalid provider identifier {provider!r} in {uri!r}")

    return Locator(
        scheme="desdeo",
        op=op,
        provider=provider,
        raw=uri,
        http_url=None,
    )


class Provider(Protocol):
    """The minimal interface any implemented provider should fulfill."""

    def info(self, params: ExternalProblemParams) -> ExternalProblemInfo:
        """Return the information of an external problem the provider exposes.

        Args:
            params (ExternalProblemParams): the parameters to generate the external problem.

        Returns:
            ExternalProblemInfo: information on the external problem.
        """

    def evaluate(
        self, xs: dict[str, VariableType | list[VariableType]], params: ProviderParams | dict[str, Any]
    ) -> dict[str, float]:
        """Given a set of variable values, evalate the external problem.

        Args:
            xs (dict[str, VariableType]): a set of variables to be evaluated.
                Expected format is {variable symbol: [values]}.
            params (ProviderParams | dict[str, Any]): the parameters that can be used to generate the external problem.
                Can also be a dict.

        Returns:
            dict[str, float]: a dict with keys corresponding to evaluated fields of the problem, e.g.,
                objective functions, constraints, etc., and values consisting of lists.

        Note:
            When multiple values are provided for the variables, it is assumed that
            the external problem is evaluated pointwise and that the returned values
            correspond to the input values in the same order.
        """


class UnknownProviderError(KeyError):
    """Raised when a non-existing provider is encountered."""


class ProviderRegistry:
    """A registry of available providers."""

    def __init__(self) -> None:
        """Initializes the registry with an empty listing of providers."""
        self._providers: dict[str, Provider] = {}

    def register(self, name: str, provider: Provider) -> None:
        """Register a new provider.

        Args:
            name (str): the name of the provider.
            provider (Provider): the provider to be registered.
        """
        self._providers[name] = provider

    def get(self, name: str) -> Provider:
        """Get a provider from the registry based on its name."""
        try:
            return self._providers[name]
        except KeyError as e:
            raise UnknownProviderError(f"Unknown provider: {name!r}") from e

    def has(self, name: str) -> bool:
        """Checks if a provider already exists in the registry.

        Args:
            name (str): name of the provider.

        Returns:
            bool: whether it exists in the registry.
        """
        return name in self._providers

    def items(self) -> list[Provider]:
        """Return the current providers in the registry.

        Returns:
            list[Provider]: list with the providers in the registry.
        """
        return self._providers.items()


class ProviderResolverError(RuntimeError):
    """Raised when the resolver fails to resolve to an existing simulator."""


def _stable_json(d: dict[str, Any]) -> str:
    # stable key for caching etc.
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


class ProviderResolver:
    """Defines a resolver for registered providers."""

    def __init__(self, registry: ProviderRegistry) -> None:
        """Initialize the resolver with a registry of providers.

        Args:
            registry (ProviderRegistry): a registry of providers the resolver should be aware of.
        """
        self.registry = registry
        self._info_cache: dict[tuple[str, str], dict[str, Any]] = {}

    def clear_caches(self) -> None:
        """Clears the info cache."""
        self._info_cache.clear()

    def info(self, locator_uri: str, params: dict[str, Any]) -> ExternalProblemInfo:
        """Get info on the problem from the resolved provider.

        Args:
            locator_uri (str): the uri to locate the provider of the problem's info.
            params (dict[str, Any]): parameters given to the provider.

        Raises:
            ProviderResolverError: when the provider cannot be resolved.

        Returns:
            dict[str, Any]:
        """
        loc = parse_locator(locator_uri)

        if loc.scheme == "http":
            raise ProviderResolverError("TODO: HTTP info not implemented.")

        if loc.provider is None:
            raise ProviderResolverError("Could not resolve the provider.")

        cache_key = (loc.provider, _stable_json(params))

        if cache_key in self._info_cache:
            return self._info_cache[cache_key]

        provider = self.registry.get(loc.provider)
        out = provider.info(params)

        self._info_cache[cache_key] = out

        return out

    def evaluate(
        self,
        locator_uri: str,
        params: ProviderParams | dict[str, Any],
        xs: dict[str, VariableType | list[VariableType]],
    ) -> dict[str, float]:
        """Evaluate the problem with a resolved provider.

        Args:
            locator_uri (str): the uri to locate the provider.
            params (ProviderParams | dict[str, Any]): parameters given to the provider.
            xs (dict[str, VariableType]): a set of variables to be evaluated.
                Expected format is {variable symbol: [values]}.

        Raises:
            ProviderResolverError: could not evaluate the problem.

        Returns:
            dict[str, float]: a dict with keys corresponding to evaluated fields of the problem, e.g.,
                objective functions, constraints, etc., and values consisting of lists.

        Note:
            When multiple values are provided for the variables, it is assumed that
            the external problem is evaluated pointwise and that the returned values
            correspond to the input values in the same order.
        """
        loc = parse_locator(locator_uri)
        if loc.scheme == "http":
            # remote
            try:
                r = requests.post(loc.http_url, json={"params": params, "X": xs}, timeout=30)
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                raise ProviderResolverError(f"HTTP evaluation failed for {loc.http_url!r}") from e

        if loc.provider is None:
            raise ProviderResolverError("Could not resolve the provider.")

        provider = self.registry.get(loc.provider)

        return provider.evaluate(xs, params)
