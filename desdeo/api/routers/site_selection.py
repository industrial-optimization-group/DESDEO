"""Endpoints for site selection map visualization and metadata management."""

import json
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import ProblemDB, ProblemMetaDataDB, SiteSelectionMetaData, User
from desdeo.api.routers.user_authentication import get_current_user

router = APIRouter(prefix="/site-selection", tags=["Site Selection"])

# Color constants for map nodes
COLOR_ACTIVE = "#FFA500"  # node has at least one visited site
COLOR_COVERED = "#FFFF00"  # node is covered by a nearby visited site
COLOR_INACTIVE = "#808080"  # node is not covered


# --- Request / Response models ---


class SiteSelectionMetaDataRequest(BaseModel):
    """Request body for loading site selection metadata."""

    problem_id: int
    sites: list[dict]  # [{name, node, lat, lon}]
    nodes: list[dict]  # [{name, lat, lon, size}]
    travel_time_matrix: list[list[float]]
    site_variable_symbols: list[str]
    coverage_variable_symbols: list[str] | None = None
    coverage_threshold: float = 15.0


class SiteSelectionMapRequest(BaseModel):
    """Request body for building the site selection map."""

    problem_id: int
    optimal_variables: dict  # from SolverResults.optimal_variables


class SiteSelectionMapNode(BaseModel):
    """A node marker on the map."""

    name: str
    lat: float
    lon: float
    size: float
    color: str
    tooltip: str


class SiteSelectionMapEdge(BaseModel):
    """A coverage connection edge between two nodes."""

    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float


class SiteSelectionMapResponse(BaseModel):
    """Response body for the site selection map endpoint."""

    nodes: list[SiteSelectionMapNode]
    edges: list[SiteSelectionMapEdge]
    center: list[float]


# --- Endpoints ---


@router.post("/load_metadata")
def load_metadata(
    req: SiteSelectionMetaDataRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> SiteSelectionMetaData:
    """Store site selection metadata for a problem.

    The authenticated user must own the problem.
    """
    problem = session.get(ProblemDB, req.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"Problem with ID {req.problem_id} not found.")

    if problem.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this problem.")

    # Ensure ProblemMetaDataDB exists for this problem
    metadata_db = session.exec(select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == req.problem_id)).first()
    if metadata_db is None:
        metadata_db = ProblemMetaDataDB(problem_id=req.problem_id)
        session.add(metadata_db)
        session.commit()
        session.refresh(metadata_db)

    site_sel = SiteSelectionMetaData(
        metadata_id=metadata_db.id,
        sites_json=json.dumps(req.sites),
        nodes_json=json.dumps(req.nodes),
        travel_time_matrix_json=json.dumps(req.travel_time_matrix),
        site_variable_symbols=req.site_variable_symbols,
        coverage_variable_symbols=req.coverage_variable_symbols,
        coverage_threshold=req.coverage_threshold,
    )
    session.add(site_sel)
    session.commit()
    session.refresh(site_sel)

    return site_sel


@router.post("/map", response_model=SiteSelectionMapResponse)
def build_map(
    req: SiteSelectionMapRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> SiteSelectionMapResponse:
    """Build Leaflet-compatible map data from a site selection solution.

    Reads site selection metadata from the DB and extracts variable values
    from the provided solution to determine node colors and coverage edges.
    """
    # Load metadata
    metadata_db = session.exec(select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == req.problem_id)).first()

    if metadata_db is None:
        raise HTTPException(status_code=404, detail="No metadata found for this problem.")

    site_sel_list = [m for m in metadata_db.all_metadata if m.metadata_type == "site_selection_metadata"]
    if not site_sel_list:
        raise HTTPException(status_code=404, detail="No site selection metadata found for this problem.")

    meta: SiteSelectionMetaData = site_sel_list[-1]

    # Parse embedded JSON
    sites: list[dict] = json.loads(meta.sites_json)
    nodes: list[dict] = json.loads(meta.nodes_json)
    ttime_matrix: list[list[float]] = json.loads(meta.travel_time_matrix_json)

    n_nodes = len(nodes)
    n_sites = len(sites)

    # Extract site visit values from solution variables
    sv = []
    for sym in meta.site_variable_symbols:
        val = req.optimal_variables.get(sym)
        if isinstance(val, list):
            sv.append(bool(round(val[0])))
        elif val is not None:
            sv.append(bool(round(val)))
        else:
            sv.append(False)

    # Extract coverage values
    cover = []
    if meta.coverage_variable_symbols:
        for sym in meta.coverage_variable_symbols:
            val = req.optimal_variables.get(sym)
            if isinstance(val, list):
                cover.append(bool(round(val[0])))
            elif val is not None:
                cover.append(bool(round(val)))
            else:
                cover.append(False)
    else:
        cover = [False] * n_nodes

    visited_site_indices = [i for i, v in enumerate(sv) if v]
    covered_node_indices = [i for i, v in enumerate(cover) if v]

    # Build node name lookup
    node_names = [n["name"] for n in nodes]
    node_name_to_idx = {name: i for i, name in enumerate(node_names)}

    # Build travel-time close-nodes mask: shape (n_nodes, n_nodes)
    ttime_np = np.array(ttime_matrix)
    close_nodes = (ttime_np < meta.coverage_threshold).astype(np.int8)

    # Each site maps to its host node -> build (n_sites, n_nodes) adjacency
    site_node_names = [s["node"] for s in sites]
    site_node_idxs = [node_name_to_idx[n] for n in site_node_names]
    sites_adj2nodes = close_nodes[site_node_idxs, :]  # (n_sites, n_nodes)

    # Group visited sites by node (for tooltips)
    sites_in_nodes: dict[str, list[str]] = {}
    for i in visited_site_indices:
        node_name = site_node_names[i]
        site_name = sites[i]["name"]
        sites_in_nodes.setdefault(node_name, []).append(site_name)

    active_node_names = set(sites_in_nodes.keys())
    covered_node_names = {node_names[i] for i in covered_node_indices}

    # Build coverage connections: site_node -> set of nearby nodes it covers
    site2covered: dict[str, set[str]] = {}
    for site_idx in visited_site_indices:
        site_node = site_node_names[site_idx]
        nearby: set[str] = set()
        for n_idx in range(n_nodes):
            if sites_adj2nodes[site_idx, n_idx]:
                nearby.add(node_names[n_idx])
        nearby.discard(site_node)
        if nearby:
            existing = site2covered.get(site_node, set())
            site2covered[site_node] = existing | nearby

    # Invert: covered_node -> set of site-nodes that cover it
    adjacent_sites: dict[str, set[str]] = {}
    for site_node, covered_set in site2covered.items():
        for cov_node in covered_set:
            if cov_node in covered_node_names or cov_node in active_node_names:
                adjacent_sites.setdefault(cov_node, set()).add(site_node)

    # Coordinate lookup
    node_coords: dict[str, tuple[float, float]] = {}
    for n in nodes:
        node_coords[n["name"]] = (n["lat"], n["lon"])

    # Build edges
    edges: list[SiteSelectionMapEdge] = []
    for cov_node, src_nodes in adjacent_sites.items():
        to_lat, to_lon = node_coords[cov_node]
        for src_node in src_nodes:
            from_lat, from_lon = node_coords[src_node]
            edges.append(SiteSelectionMapEdge(from_lat=from_lat, from_lon=from_lon, to_lat=to_lat, to_lon=to_lon))

    # Build node markers
    nodes_out: list[SiteSelectionMapNode] = []
    for n in nodes:
        name = n["name"]
        lat = n["lat"]
        lon = n["lon"]
        size = n.get("size", 5.0)

        # Color assignment
        if name in active_node_names:
            color = COLOR_ACTIVE
        elif name in covered_node_names:
            color = COLOR_COVERED
        else:
            color = COLOR_INACTIVE

        # Tooltip HTML
        if name in sites_in_nodes:
            site_list_html = "<br>".join(sites_in_nodes[name])
            tooltip = f"<b>{name}</b><br><b>Sites:</b><br>{site_list_html}"
        elif name in adjacent_sites:
            covered_by = "<br>".join(sorted(adjacent_sites[name]))
            tooltip = f"<b>{name}</b><br><b>Covered by sites in:</b><br>{covered_by}"
        else:
            tooltip = f"<b>{name}</b>"

        nodes_out.append(SiteSelectionMapNode(name=name, lat=lat, lon=lon, size=size, color=color, tooltip=tooltip))

    # Center of the map
    avg_lat = sum(n.lat for n in nodes_out) / len(nodes_out)
    avg_lon = sum(n.lon for n in nodes_out) / len(nodes_out)

    return SiteSelectionMapResponse(nodes=nodes_out, edges=edges, center=[avg_lat, avg_lon])
