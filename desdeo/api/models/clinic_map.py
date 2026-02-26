"""Models for the clinic map visualization endpoint."""

from pydantic import BaseModel


class ClinicMapRequest(BaseModel):
    """Request body for the clinic map endpoint.

    Attributes:
        sv: Binary vector of length 60 indicating visited sites.
        cover: Binary vector of length 36 indicating covered cities.
    """

    sv: list[float]
    cover: list[float]


class ClinicMapCity(BaseModel):
    """A city marker on the map."""

    city: str
    lat: float
    lon: float
    size: float
    color: str
    tooltip: str


class ClinicMapLine(BaseModel):
    """A coverage connection line between two cities."""

    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float


class ClinicMapResponse(BaseModel):
    """Response body for the clinic map endpoint."""

    cities: list[ClinicMapCity]
    lines: list[ClinicMapLine]
    center: list[float]
