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

---

## [2.4.0] - 14.4.2026

### Core logic

#### Added

- Added **CVXPY solver** support with full integration into the problem/solver
  stack (#466).
- Updated `guess_best_solver` to include CVXPY and to check for a valid Gurobi
  license (#468).

#### Changed

- Updated **gurobipy** implementation: tensor constants can now be used without
  errors (#464).

#### Fixed

- Fixed infinite loop in `dmitry_forest_problem_disc()` (use relative path
  instead of walking up to the `DESDEO` folder), which also caused
  `conftest.py` to hang.

---

### Web API

#### Added

- Added **NAUTILUS Navigator** endpoints `/initialize` and `/navigate`, with
  `NautilusNavigatorInitializationState` and `NautilusNavigatorNavigationState`
  states and unit tests.
- Added **constrained variant** endpoint
  `POST /problem/{problem_id}/constrained_variant` with `VariableFixing`,
  `ConstrainedVariantRequest`, and `ConstrainedVariantResponse` models.
- Added `is_temporary` and `parent_problem_id` fields to `ProblemDB` for
  variant tracking.
- Added **site-selection** endpoints `POST /site-selection/load_metadata` and
  `POST /site-selection/map`, backed by a new `SiteSelectionMetaData` DB model
  (follows the `ForestProblemMetaData` pattern).
- Added **E-NAUTILUS what-if simulation** endpoint
  `POST /method/enautilus/simulate` (ephemeral, no DB writes) with
  `ENautilusSimulateRequest`/`Response`/`StepResult` models and a
  `deprioritize` flag for worst-case selection.
- Added endpoint returning the list of **DM users**.
- Added `/add_new_dm` endpoint (restricted to analyst/admin) and enabled
  analysts/admins to create and manage problems and interactive sessions on
  behalf of DMs.
- Added `fetch_problem_with_role_check` and
  `fetch_interactive_session_with_role_check` helpers in `utils.py` for
  role-aware ownership bypass.
- Added `?target_user_id=` parameter on `POST /session/new` for analysts to
  create sessions on behalf of DMs.
- Added endpoint returning an HTTP exception based on an error code.
- Added tests for the constrained-variant endpoint, the site-selection
  endpoint, and DM-user/problem-ownership behavior.

#### Changed

- Refactored **NAUTILUS Navigator** to follow the E-NAUTILUS patterns: replaced
  legacy manual auth/problem loading with `SessionContextGuard`, moved
  request/response models from `schemas/` to `models/` as `SQLModel`, used
  `Problem.from_problemdb()`, and walked `StateDB.parent` for session-scoped
  parent-chain traversal.
- Deleted `desdeo/api/schemas/` (no longer needed after the model migration).
- Session/problem listing endpoints now return all sessions/problems for
  analysts (own only for DMs); empty lists return `200 + []` instead of `404`.
- Problem action endpoints (delete, solver, JSON, representative sets) now
  allow analyst access to any problem.
- Simplified `DELETE /problem/{problem_id}`: owners can delete any of their
  problems.
- Restricted `POST /add_new_dm` to analyst/admin (was previously public).
- Removed the legacy `/clinic/` router, `ClinicMapRequest`/`Response` models,
  and `clinic_map.py` in favor of the metadata-driven site-selection map.
- Added `401` and `500` login responses to the API/OpenAPI generator.

#### Fixed

- Fixed `SessionContextGuard` HTTP status codes: `404` for missing resources,
  `403` for ownership failures (previously `400` for both).
- Fixed `InteractiveSessionBase` missing `from_attributes=True`, which caused
  `POST /session/new` to return `{}`.
- Fixed swapped arguments in `fetch_interactive_session` (utils.py).
- Fixed `test_delete_problem_unauthorized` and `test_constraint_variant` to
  expect the correct `403`/`404` status codes.

---

### Web GUI

#### Added

- Added rudimentary **Manage Users** page (`/manage-users`) for analysts and
  admins to create DM and analyst accounts; route is server-side guarded and nav
  visibility is role-based (auth store populated on topbar mount).
- Added analyst/admin management of other users' interactive sessions and
  problems: user filter dropdown (default "Myself"), Owner column/field, and
  "Create for" / DM selectors on session and problem creation.
- Added **map metadata upload** dialog on the Problems page (JSON file
  upload); renamed `clinic-map.svelte` to `site-selection-map.svelte` which
  now accepts a `problem_id` prop.
- Added **map interaction** in E-NAUTILUS: click site markers to cycle
  free → restricted → forced; multiple sites per city node are constrained
  together; re-solve with RPM using E-NAUTILUS final objectives as aspiration
  levels; constrained variant inherits the parent problem's solver metadata.
- Added comparison bottom panel with tabbed **Parallel Coordinates /
  Comparison Table** views; solution tab shows the constrained solution with
  the original as a dashed comparison line; "Use this solution" accepts the
  constrained result, "Reset" reverts to the original.
- Added **what-if scenario simulation** in the Decision Journey view: "best"
  (blue) and "worst" (red) buttons per objective, dashed-line overlays with
  hollow-circle markers, and an actual-vs-what-if comparison table with
  colored deltas.
- Added catch-all proxy route `/api/[...path]` that forwards browser API
  calls through `event.fetch` so `handleFetch` intercepts for cookie
  injection and `401`/token-refresh handling.
- Added generated Orval endpoints for NAUTILUS Navigator and enabled Orval
  Zod body-schema generation.
- Added login error display after unsuccessful login attempts.

#### Changed

- Replaced the hardcoded clinic map system with the new metadata-driven
  site-selection map.
- Unrolled tensor variables in RPM results for frontend compatibility
  (e.g. `sv` → `sv_1..sv_60`).
- Updated API client to use correct URLs for debug/deploy; `getUrl` now
  returns a relative `/api/<path>` on the browser side, with a
  `http://localhost:8000` fallback detected via `typeof window === 'undefined'`
  on the server side.
- Removed client-side `401` retry logic from `customFetch` — now handled
  server-side by `handleFetch` via the proxy; removed the dead Vite `/api`
  proxy config from `vite.config.ts`.
- Replaced `$effect` with an explicit `oninput` handler for clearing login
  errors and removed a debug `console.log` from the login server action.
- Default Decision Journey visualization pane height raised to 65% for more
  chart room; selected iteration highlighted with a vertical band.
- Regenerated Orval clients multiple times to pick up new endpoints.

#### Fixed

- Fixed various URL-resolving and access-token cookie issues affecting
  deployment.
- Fixed Orval import mismatches after regeneration
  (`getProblemProblemGetPost`, `addRepresentativeSolutionSet`).

---

### Documentation

#### Added

- Added a guide on how to deploy the fullstack on **OpenShift** using the
  `oc` tool from a terminal.

#### Changed

- Updated deployment documentation and polished deployment files.
- Updated the `webui` README (including the `API_BASE_URL` fix).

---

### Tooling, CI, and deployment

#### Added

- Added a **`justfile`** and the `rust-just` dependency — `just` is a
  drop-in cross-platform replacement for `make` and is available on PyPI.
- Added a Python version of `run_fullstack.sh` so it runs on all
  Python-compatible platforms.
- Added a GitHub workflow for running the Web GUI tests with Vite.
- Added `secrets` to `.gitignore`.

#### Changed

- Updated docs so that references to `make`/`Makefile` now point to
  `just`/`justfile`.
- Updated build and Dockerfiles; switched `npm ci` to `npm install` in
  `webui/Dockerfile`.
- General Rahti deployment testing and configuration updates.

---

## [2.3.0] - 31.3.2026

### Core logic

#### Added

- Added `lagrange_multipliers` field to `SolverResults`; extract duals from
  Ipopt, Bonmin, and Gurobi solvers.
- Added `desdeo/explanations/lagrange.py` with filter, tradeoff, and
  active-objective utilities for Lagrange multiplier analysis.
- Added unit tests for Lagrange utilities and solver integration tests.

#### Fixed

- Fixed a bug where `ScipyMinimizeSolver` and `ScipyDeSolver` returned incorrect
  solutions for problems with `maximize=True` objectives.
- Fixed infinite loop in the Dmitry forest problem (use
  `Path(__file__).resolve()` instead of searching for `"DESDEO"` folder name).

---

### Web API

#### Added

- Added `get-multipliers-info` endpoint to the NIMBUS router.
- Added XNIMBUS (Explainable NIMBUS) `StateKinds`, state fields, and API
  models (`NIMBUSMultiplierRequest`/`Response`).
- Added XNIMBUS router with explainability endpoints; registered in `app.py`.
- Added XNIMBUS API endpoint tests.

#### Changed

- Removed singleton request model classes (`ProblemGetRequest`,
  `GetSessionRequest`, `RepresentativeSolutionSetRequest`) and refactored
  endpoints to use query parameters instead.
- Refactored `SessionContextGuard`: replaced `__call__` with
  `.post`/`.get`/`.delete` methods to eliminate spurious `requestBody` on
  GET/DELETE endpoints in the OpenAPI schema.
- Fixed `SessionContextGuard` swapped-arguments bug (`fetch_interactive_session`
  called with request/session reversed).

#### Fixed

- Fixed cookies being set to `Secure` in dev mode, which broke the UI over HTTP
  connections (e.g., WSL). The `Secure` flag is now derived from the SvelteKit
  `dev` environment setting.

---

### Web GUI

#### Added

- Added XNIMBUS (Explainable NIMBUS) frontend route with explainable layout,
  advanced sidebar, explanation bar charts, and help dialog.
- Added Explainable NIMBUS to the method selection/initialize view.
- Added custom 404 error page.
- Added registration and forgot-password placeholder pages; fixed links
  on the login page.
- Added visual indicators on the login form.
- Added page titles and meta descriptions to all frontend routes.

#### Changed

- Fully migrated to Orval-generated endpoints: replaced all `api.GET`/`api.POST`
  calls with Orval-generated endpoint functions across 19 files (problems, groups,
  NIMBUS, XNIMBUS, SCORE-bands, GDM-SCORE-bands, GNIMBUS, EMO routes).
- Consolidated Orval-generated models and clients into a single file instead of
  splitting across `src/lib/gen/models`.
- Migrated all `components['schemas']` references to direct `$lib/gen/models`
  imports.
- Refactored NIMBUS frontend to Orval handler pattern (removed `+server.ts`
  proxy, `callNimbusAPI`).
- Refactored GNIMBUS `+server.ts` from generic dispatch to individual Orval
  calls.
- Removed unused client files: `client.ts`, `client-types.ts`, `zod-schemas.ts`,
  `zod-types.ts`.
- Removed `openapi-fetch` and `openapi-typescript-fetch` dependencies.
- Renamed "Worsen until" to "Impair until" in NIMBUS constants.

#### Fixed

- Fixed Orval GET-with-body error (pass `undefined` instead of `null` for
  optional body params).
- Fixed stale Orval imports in E-NAUTILUS, problems/handler, and
  problems/define/handler.
- Fixed explanation bar chart / ranking bar chart label overflow (rotate,
  truncate, cap margins).

---

### Documentation

#### Added

- Added guide on how to implement method interfaces in the GUI.

#### Changed

- Updated contributing guide to include instructions for running tests without
  `make`.
- Updated installation documentation for DESDEO on JYU Windows.
- Fixed improperly formatted MkDocs settings for Read the Docs builds.
- Fixed broken cross-references in notebook markdown cells (autorefs to standard
  links).
- Completed sympy evaluator, Pyomo solvers, Nevergrad solver, and Summary of
  Solvers documentation sections.
- Made all documentation code cells executable with real test problems.
- Suppressed sklearn and COBYLA warnings in documentation notebooks.

---

## [2.2.2] - 17.2.2026

### Core logic

_(No core-logic changes in this release.)_

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

_(No functional API changes in this release.)_

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
