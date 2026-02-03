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

## [2.2.0] - 2026-02-03

### Core logic
#### Added
- Added a **seeded population generator** for evolutionary multiobjective optimization:
  - Supports generating populations by perturbing a provided seed solution.
  - Allows controlling the ratio of seeded vs. random solutions.
  - Supports all variable types.

#### Fixed
- Fixed issues in the seeded generator implementation discovered during integration and testing.

---

### Web API
#### Changed
- Refactored session context handling:
  - `get_session_context` is now used consistently in the endpoints.
  - Removed redundant checks around interactive state retrieval; invalid states now raise immediately.
- Applied linter-driven cleanup (removal of deprecated imports, improved import ordering, minor syntax fixes).
- Access tokens are now returned as cookies as well (previously this was a feature just for refresh tokens).

---

### Web GUI
#### Added
- Added a **problem definition page** (WIP), including:
  - Initial problem definition form.
  - Iterative refinements to structure and validation.
- Added initial support for **selecting interactive sessions** in the method-selection view, analogous to problem selection.

#### Changed
- Improved E-NAUTILUS session startup and validation logic.
- Updated session and startup inputs for E-NAUTILUS.
- Fixed missing session information in the E-NAUTILUS `selection` state.
- Refined session settings UI for E-NAUTILUS.
- Improved authentication flow by refreshing access tokens on `401` responses and updating cookies accordingly.

#### Known issues
- Deleting sessions can currently break NIMBUS if it attempts to access states from a deleted session.

---

### Tests
#### Changed
- Improved `Makefile` test rules:
  - Better handling of skipped tests.
  - Added a dedicated `make test-api` rule.
  - General cleanup and variable handling improvements.
- Fixed test setup issues on the home page.

---

### Tooling, CI, and linting
#### Changed
- Applied extensive **ruff-based linting fixes** across the codebase.
- Cleaned up code to satisfy pre-commit hooks.
- Minor workflow and maintenance-related refinements.

---

### Documentation
#### Changed
- Updated `README.md`:
  - Clarified the development status of the Web GUI.
  - Updated installation instructions.
  - Revised funding information.
  - Reordered and expanded project badges, including PyPI version badge.
- Minor documentation fixes and clarifications.

---

### Notes
- Several components (notably the Web GUI and session management) remain **actively evolving research prototypes**.

---

## [2.1.1] - 2026-01-27

### Core logic
#### Changed
- Updated `CBCOptions` parameter name from `sec` to `seconds` to better reflect semantics.
- Removed obsolete pytest tags (`nogithub`) as part of test cleanup.

---

### Web API
*(No functional API changes in this release.)*

---

### Web GUI
#### Added
- Added a **barebones page for adding and inspecting interactive sessions** (WIP).

---

### Tests
#### Changed
- Cleaned up pytest markers:
  - Re-added `githubskip` where appropriate.
  - Removed excessive pytest tags that were unintentionally skipping tests.
  - Added a new `fixme` pytest mark to explicitly label known failing tests with pending issues.
- Updated pytest commands in the `Makefile`.

---

### Workflows / CI
#### Added
- Added a **pre-commit hook GitHub workflow** that runs checks only on changed files in pull requests.
- Integrated **ruff-based linting and formatting** via pre-commit hooks.
- For details about pre-commit hooks (how to install and activate),
  see [the documentation](https://desdeo.readthedocs.io/en/latest/tutorials/contributing/#pre-commit-hooks).

#### Changed
- Updated unit test workflow:
  - Now runs on `master` branch commits and pull requests.
  - Switched dependency management from `pip` to **`uv`**.
  - Added missing pytest tags to ensure correct test selection.

---

### Tooling and linting
#### Changed
- Removed `isort` in favor of **ruff-only** linting and formatting.
- Refined ruff configuration in `pyproject.toml` to be more sensible in practice.
- Fixed minor linting issues revealed by enabling pre-commit hooks.

---

### Documentation
#### Changed
- Updated `README.md`.
- Updated contributing documentation with instructions and expectations for using pre-commit hooks.

---

### Notes
- This release focuses on **developer experience, CI correctness, and test hygiene**.
- No user-facing web-API changes are expected.
- GUI additions are **early-stage and exploratory**.

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
