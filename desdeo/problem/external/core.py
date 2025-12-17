"""Implements a interface to interface into external (test) problem suites."""

import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlparse

import requests

Op = Literal["info", "evaluate"]
Kind = Literal["desdeo", "http"]


@dataclass(frozen=True)
class Locator:
    kind: Kind
    op: Op | None
    provider: str | None
    raw: str

    # for http
    http_url: str | None = None


class LocatorParseError(ValueError):
    pass


def parse_locator(uri: str) -> Locator:
    p = urlparse(uri)

    if p.scheme in ("http", "https"):
        segments = [s for s in p.path.split("/") if s]
        if len(segments) == 2:
            provider, op = segments
        else:
            raise LocatorParseError(f"Invalid path; expected 2 segments in {uri!r}")

        return Locator(
            kind="http",
            op=None,
            provider=None,
            raw=uri,
            http_url=uri,
        )

    if p.scheme != "desdeo":
        raise LocatorParseError(f"Unsupported scheme: {p.scheme!r} in {uri!r}")

    segments = [s for s in p.path.split("/") if s]
    if len(segments) == 2:
        provider, op = segments
    else:
        raise LocatorParseError(f"Invalid path; expected 2 segments in {uri!r}")

    if op not in ("info", "evaluate"):
        raise LocatorParseError(f"Unsupported operation {op!r} in {uri!r}")

    if not provider or not (provider[0].isalpha() and all(c.isalnum() or c in "_-" for c in provider)):
        raise LocatorParseError(f"Invalid provider identifier {provider!r} in {uri!r}")

    return Locator(
        kind="desdeo",
        op=op,
        provider=provider,
        raw=uri,
        http_url=None,
    )


class Provider(Protocol):
    def info(self, params: dict[str, Any]) -> dict[str, Any]: ...

    def evaluate(self, X: list[list[float]], params: dict[str, Any]) -> dict[str, Any]: ...


class UnknownProviderError(KeyError):
    pass


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, name: str, provider: Provider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> Provider:
        try:
            return self._providers[name]
        except KeyError as e:
            raise UnknownProviderError(f"Unknown provider: {name!r}") from e


class SimulatorResolveError(RuntimeError):
    pass


def _stable_json(d: dict[str, Any]) -> str:
    # stable key for caching etc.
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


class SimulatorResolver:
    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry
        self._info_cache: dict[tuple[str, str], dict[str, Any]] = {}

    def info(self, locator_uri: str, params: dict[str, Any]) -> dict[str, Any]:
        loc = parse_locator(locator_uri)

        if loc.kind == "http":
            raise SimulatorResolveError("TODO: HTTP info not implemented.")

        assert loc.provider is not None

        cache_key = (loc.provider, _stable_json(params))

        if cache_key in self._info_cache:
            return self._info_cache[cache_key]

        provider = self.registry.get(loc.provider)
        out = provider.info(params)

        self._info_cache[cache_key] = out

        return out

    def evaluate(self, locator_uri: str, params: dict[str, Any], X: list[list[float]]) -> dict[str, Any]:
        loc = parse_locator(locator_uri)
        if loc.kind == "http":
            # remote
            try:
                r = requests.post(loc.http_url, json={"params": params, "X": X}, timeout=30)
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                raise SimulatorResolveError(f"HTTP evaluation failed for {loc.http_url!r}") from e

        assert loc.provider is not None

        provider = self.registry.get(loc.provider)

        return provider.evaluate(X, params)
