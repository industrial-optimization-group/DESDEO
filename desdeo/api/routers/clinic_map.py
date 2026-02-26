"""Endpoint for building clinic map visualization data from a solution's binary vectors."""

from pathlib import Path

import numpy as np
import polars as pl
from fastapi import APIRouter, HTTPException

from desdeo.api.models.clinic_map import (
    ClinicMapCity,
    ClinicMapLine,
    ClinicMapRequest,
    ClinicMapResponse,
)

router = APIRouter(prefix="/clinic", tags=["Clinic"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "experiments" / "clinic" / "data"
FOOD_DESERT_THRESHOLD = 15  # minutes

N_SITES = 60
N_CITIES = 36


@router.post("/map", response_model=ClinicMapResponse)
def build_clinic_map(req: ClinicMapRequest) -> ClinicMapResponse:
    """Build Leaflet-compatible map data from a clinic solution's binary vectors.

    Takes sv (60 site-visit booleans) and cover (36 city-coverage booleans)
    and returns city markers with colors/tooltips plus coverage connection lines.
    """
    if len(req.sv) != N_SITES:
        raise HTTPException(status_code=422, detail=f"sv must have {N_SITES} values, got {len(req.sv)}")
    if len(req.cover) != N_CITIES:
        raise HTTPException(status_code=422, detail=f"cover must have {N_CITIES} values, got {len(req.cover)}")

    # --- Load static data ---
    cities_df = pl.read_csv(DATA_DIR / "cities.csv")
    sites_df = pl.read_csv(DATA_DIR / "proposedSitesProcessed.csv")
    adj_ttime_df = pl.read_csv(DATA_DIR / "adjacencyMatrixTravelTime.csv")

    all_city_names: list[str] = cities_df["city"].to_list()
    site_city_names: list[str] = sites_df["city"].to_list()

    # --- Parse binary vectors ---
    sv = [bool(round(v)) for v in req.sv]
    cover = [bool(round(v)) for v in req.cover]

    visited_site_indices = [i for i, v in enumerate(sv) if v]
    covered_city_indices = [i for i, v in enumerate(cover) if v]

    # --- Build travel-time adjacency (36x36) and close-cities mask ---
    ttime_city_names = adj_ttime_df.columns[1:]  # 36 city column names
    ttime_matrix = adj_ttime_df.select(ttime_city_names).to_numpy()  # (36, 36)
    city_to_idx = {name: i for i, name in enumerate(ttime_city_names)}

    close_cities = (ttime_matrix < FOOD_DESERT_THRESHOLD).astype(np.int8)  # (36, 36)

    # Each site inherits the adjacency row of its host city → (60, 36)
    site_city_idxs = [city_to_idx[c] for c in site_city_names]
    cities_adj2sites = close_cities[site_city_idxs, :]  # (60, 36)

    # --- Group visited sites by city (for tooltips) ---
    sites_in_cities: dict[str, list[str]] = {}
    for i in visited_site_indices:
        city = site_city_names[i]
        name = sites_df["siteName"][i]
        sites_in_cities.setdefault(city, []).append(name)

    event_city_names = set(sites_in_cities.keys())
    covered_city_names = {all_city_names[i] for i in covered_city_indices}

    # --- Build coverage connections ---
    # For each visited site, find which cities it covers (within threshold)
    visited_site_city_list = [site_city_names[i] for i in visited_site_indices]

    # site_city → set of nearby cities it covers (excluding itself)
    site2covered: dict[str, set[str]] = {}
    for idx_in_visited, site_idx in enumerate(visited_site_indices):
        site_city = site_city_names[site_idx]
        nearby: set[str] = set()
        for c_idx in range(N_CITIES):
            if cities_adj2sites[site_idx, c_idx]:
                nearby.add(all_city_names[c_idx])
        nearby.discard(site_city)
        if nearby:
            existing = site2covered.get(site_city, set())
            site2covered[site_city] = existing | nearby

    # Invert: covered_city → set of site-cities that cover it.
    # Only include cities that are actually covered (cover=1) or have events,
    # not just physically nearby. The cover vector is a solver decision —
    # a city can be within threshold but uncovered when the epsilon constraint
    # on f_4 is loose.
    adjacent_sites: dict[str, set[str]] = {}
    for site_city, covered_set in site2covered.items():
        for cov_city in covered_set:
            if cov_city in covered_city_names or cov_city in event_city_names:
                adjacent_sites.setdefault(cov_city, set()).add(site_city)

    # --- Coordinate lookup ---
    city_coords: dict[str, tuple[float, float]] = {}
    for row in cities_df.iter_rows(named=True):
        city_coords[row["city"]] = (row["lat"], row["long"])

    # --- Build lines with resolved coordinates ---
    lines: list[ClinicMapLine] = []
    for cov_city, src_cities in adjacent_sites.items():
        to_lat, to_lon = city_coords[cov_city]
        for src_city in src_cities:
            from_lat, from_lon = city_coords[src_city]
            lines.append(ClinicMapLine(from_lat=from_lat, from_lon=from_lon, to_lat=to_lat, to_lon=to_lon))

    # --- Build city markers ---
    cities_out: list[ClinicMapCity] = []
    for row in cities_df.iter_rows(named=True):
        city_name: str = row["city"]
        lat: float = row["lat"]
        lon: float = row["long"]
        pop: int = row["pop"]

        # Color assignment
        if city_name in event_city_names:
            color = "orange"
        elif city_name in covered_city_names:
            color = "yellow"
        else:
            color = "grey"

        size = max(5.0, pop / 1000)

        # Tooltip HTML
        if city_name in sites_in_cities:
            site_list_html = "<br>".join(sites_in_cities[city_name])
            tooltip = (
                f"<b>{city_name}</b><br>"
                f"<b>Population:</b> {pop}<br>"
                f"<b>Sites with events:</b><br>{site_list_html}"
            )
        elif city_name in adjacent_sites:
            covered_by = "<br>".join(sorted(adjacent_sites[city_name]))
            tooltip = (
                f"<b>{city_name}</b><br>"
                f"<b>Population:</b> {pop}<br>"
                f"<b>No Healthwise Clinics</b><br>"
                f"<b>Covered by events in:</b><br>{covered_by}"
            )
        else:
            tooltip = f"<b>{city_name}</b><br>" f"<b>Population:</b> {pop}<br>" f"<b>No Healthwise Clinics</b>"

        cities_out.append(ClinicMapCity(city=city_name, lat=lat, lon=lon, size=size, color=color, tooltip=tooltip))

    # --- Center of the map (average of all city coordinates) ---
    avg_lat = sum(c.lat for c in cities_out) / len(cities_out)
    avg_lon = sum(c.lon for c in cities_out) / len(cities_out)

    return ClinicMapResponse(cities=cities_out, lines=lines, center=[avg_lat, avg_lon])
