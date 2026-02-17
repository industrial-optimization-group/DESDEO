# Changelog

All notable changes to **DESDEO** are documented in this file.

This project follows **Keep a Changelog** and **Semantic Versioning**:
- Keep a Changelog: https://keepachangelog.com/en/1.1.0/
- SemVer: https://semver.org/
- Changelogs are generated using an LLM and curated by a human

## [Version template]

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

## [2.2.2] - 17.2.2026

### Core logic
*(No core-logic changes in this release.)*

---

### Web API
#### Added
- Added **E-NAUTILUS finalize** state and endpoint.
- Added `ENautilusTreeNodeResponse`, `ENautilusDecisionEventResponse`, and `ENautilusSessionTreeResponse` models.
- Added `GET /method/enautilus/session_tree/{session_id}` endpoint returning all nodes, edges, root IDs, and decision events.
- Added `DELETE /problem/{id}` endpoint for problem deletion.
- Added cascade deletes to `ProblemDB` relationships (solutions, preferences, states, constants, variables, objectives, constraints, etc.).
- Added `ON DELETE CASCADE` to all 15 substate foreign key definitions.
- Added unit test for problem deletion.

#### Changed
- Introduced **`SessionContextGuard`** class, replacing `get_session_context` and `get_session_context_without_request` across all endpoint routers.
- Enabled `PRAGMA foreign_keys=ON` for SQLite connections.
- Added `back_populates` for `StateDB→ProblemDB` relationship.
- Added defensive cleanup in `_attach_substate` for existing orphaned rows.

#### Fixed
- Fixed E-NAUTILUS endpoints to work with the new `SessionContextGuard`.
- Fixed orphaned substate rows causing `UNIQUE` constraint errors after session deletion.
- Added missing docstrings and fixed typos in API models and router utilities.

---

### Web GUI
#### Added
- Added experimental new features for E-NAUTILUS related to tree and decision visualization.
- Added generic **`EndStateView`** component (reuses `FinalResultTable` + CSV download).
- Added **representative solution set selector** to E-NAUTILUS initialization panel; auto-selects when only one set exists, shows warning when none available.
- Added inline session creation with **Combobox dropdown** and "+ New" button for E-NAUTILUS.
- Added **delete and download actions** to problems data table.
- Added input confirmation dialog component.
- Added `syncProblem()` to `methodSelection` store (updates `problem_id` without clearing session/method).

#### Changed
- Replaced E-NAUTILUS final JSON view with `EndStateView`; show only the selected solution.
- Replaced final view toggle buttons with proper **Tabs** component (experimental).
- Replaced dialog-based formulation views with inline expandable rows in Objectives, Constraints, and Extra Functions tabs.
- Replaced plain HTML intermediate points table with **TanStack/sortable table** using colored headers, closeness column, and blue selection border.
- Disabled E-NAUTILUS in method initialize page when problem has no representative solution sets.
- Regenerated API client types for new E-NAUTILUS and delete endpoints.

#### Fixed
- Fixed problem context mismatch when resuming E-NAUTILUS state from a different problem.
- Fixed all `state_referenced_locally` Svelte 5 warnings across 11 components.
- Fixed Svelte 5 `$state` warnings for `bind:this` element references.
- Fixed `finalize_enautilus`: added missing return on error, cleared stale error messages.
- Excluded `mathlive` from Vite `optimizeDeps` to fix KaTeX font 404 errors.
- Disabled Finish button until intermediate point is chosen (E-NAUTILUS).
- Removed duplicate config sync effect in GDM-SCORE-bands config-panel.

## [2.2.1] - 10.2.2026

### Core logic
#### Fixed
- Fixed an issue in `PyomoEvaluator` where **equality-type (EQ) constraints were not added correctly** to the Pyomo model.
- Fixed a small bug in **GDM SCORE band computation** introduced in a previous change.

---

### Web API
#### Added
- Added support for **Representative Solution Sets**:
  - Introduced `RepresentativeSolutionSetRequest`.
  - Added endpoints to create representative solution sets.
  - Added endpoints to retrieve representative solution sets by problem ID and by set ID.
  - Added endpoint to delete a specific representative solution set.
- Added corresponding **unit tests** for representative solution set endpoints.

#### Changed
- Refactored representative solution set endpoints to use `get_session_context`.
- Removed return payload from delete endpoints where it was unnecessary.
- Minor refactoring and cleanup of API router structure.

---

### Documentation
#### Added
- Added **`llms.txt`** and **`llms-full.txt`** documentation files and integrated them into the documentation build.
- Added Read the Docs-specific configuration to ensure **notebooks are executed during RTD builds**.
- Added new Makefile rules for documentation:
  - `docs-fast`: build docs without executing notebooks.
  - `docs-rtd`: build docs with notebook execution (RTD parity).

#### Changed
- Stripped outputs from all notebooks using `nbstripout`.
- Fixed issues with notebooks not executing correctly during documentation builds.
- Polished and reorganized documentation structure (WIP).
- Added missing documentation pages to MkDocs navigation.
- Updated `README.md`:
  - Fixed links to `llms.txt` and `llms-full.txt`.
  - Minor clarifications and cosmetic updates.
- Extended contributing guidelines with additional information on pre-commit hooks.

---

### Tooling, CI, and linting
#### Added
- Added `nbstripout` as a **pre-commit hook**.

#### Changed
- Updated Read the Docs configuration to **install solver binaries** so that optimization notebooks can be executed during documentation builds.
- Refined pre-commit and ruff configuration:
  - Ignored selected boolean-argument warnings.
  - Fixed linter warnings surfaced during documentation audits.
- General cosmetic and formatting fixes across the codebase.

---

### Notes
- This iteration is **documentation- and infrastructure-heavy**, focusing on reproducibility, documentation execution fidelity, and API extensibility.
- Representative Solution Sets introduce new **decision-support abstractions** that are expected to evolve as research workflows mature.
- Several changes are **WIP and research-driven**, and interfaces may still change.

---

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
