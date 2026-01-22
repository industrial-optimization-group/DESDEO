# Changelog

All notable changes to **DESDEO** are documented in this file.

This project follows **Keep a Changelog** and **Semantic Versioning**:
- Keep a Changelog: https://keepachangelog.com/en/1.1.0/
- SemVer: https://semver.org/
- Changelogs are generated using an LLM and curated by a human

## [Unreleased]

### Core logic
#### Added
#### Changed
#### Deprecated
#### Removed
#### Fixed
#### Security

### Web API
#### Added
#### Changed
#### Deprecated
#### Removed
#### Fixed
#### Security

### Web GUI
#### Added
#### Changed
#### Deprecated
#### Removed
#### Fixed
#### Security

---

## [2.1.0] - 2026-01-22

### Core logic
#### Added
- Added **Group NIMBUS (GNIMBUS)** method to the core optimization framework.
- Added new ADM variants (ADM2, ADMAfsar) and refactored the ADM codebase with clearer base abstractions.
- Started work on a **resolver–provider–schema–based mechanism** for connecting to external test problem libraries without relying on HTTP (initial support for Pymoo-based problems).
- Added preliminary infrastructure for improved solver metadata handling.

#### Changed
- Reworked the computation of intermediate solutions (WIP) to improve numerical robustness and alignment with theoretical formulations.
- Refactored solver and reference vector handling as part of ongoing structural cleanup.

#### Fixed
- Fixed division-by-zero issues in the GUESS scalarization (implementation previously deviated from the paper).
- Fixed circular imports, mismatched parentheses, and multiple small numerical and structural issues discovered during refactoring.

#### Notes
- Several core-logic changes in this release are **experimental** and may evolve as methodological work continues.

---

### Web API
#### Added
- Added new endpoints and request models for stepping, reverting, and inspecting **E-NAUTILUS** iterations (WIP).
- Added endpoints for retrieving all iterations, votes, confirmations, and intermediate solutions in group decision-making workflows.
- Added support for defining optimization problems via **JSON file uploads**.
- Added new example problems to database initialization scripts.

#### Changed
- Refactored database session handling to propagate active sessions explicitly instead of relying on implicit generators.
- Improved authentication handling: access and refresh tokens are now supported via cookies and explicit `Authorization` headers.
- Continued work on multi-valued constraint handling and intermediate-result computation.

#### Fixed
- Fixed multiple issues in Group NIMBUS–related endpoints, including incorrect group ID usage and broken tests.
- Fixed API inconsistencies in `get_or_initialize`, utopia, and intermediate-solution endpoints.

#### Notes
- Several endpoints and request/response models should be considered **unstable** and subject to change as research workflows mature.

---

### Web GUI
#### Added
- Added initial **GNIMBUS UI** (WIP), including:
  - Group and method selection views.
  - Voting-based decision and compromise phases.
  - End-state views with objective and variable tables and CSV export.
- Added iteration history views with the ability to revert to previous iterations (WIP).
- Added real-time updates via WebSockets for phase changes, iteration updates, and voting results.
- Added new visualizations, including vote bar charts and extended parallel coordinate plot features.

#### Changed
- Migrated OpenAPI client generation to **Orval 8.x** and regenerated client models.
- Refactored preference sidebars, solution tables, and layout components for clarity and experimentation.
- Continued work on authentication and session handling in the GUI (cookies + token-based access).
- Iteratively refined dashboards, top bars, and phase-specific views.

#### Fixed
- Fixed WebSocket reconnection and shutdown handling.
- Fixed phase update propagation, layout resizing issues, tooltip rendering, and visualization inconsistencies.
- Fixed UI behavior during compromise and voting phases (e.g., disabled invalid actions, improved feedback).

#### Notes
- Large parts of the GUI remain **research prototypes**; UI structure, naming, and interaction patterns may change rapidly.

---

## [2.0.0] - 2025-05-16

### Core logic
#### Added
- Initial 2.0 release.

### Web API
#### Added
- Initial 2.0 release.

### Web GUI
#### Added
- Initial 2.0 release.