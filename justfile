# This justfile defines several recipes to run tests and other useful scripts.
#
# To execute a recipe, issue the command "just <recipe>". Requires `just`,
# which is installed automatically as a dev dependency via `uv sync`
# (PyPI package: rust-just).
#
# Run "just --list" to see all available recipes.

# Default recipe: list available recipes
default:
    @just --list

# Pytest configuration (can be overridden, e.g., `just test PYTEST_SKIP=""`)

PYTEST := "pytest -n auto"
PYTEST_SKIP := '-m "not fixme"'
PYTEST_OPTS := "--disable-warnings"
TEST_API_PATH := "./desdeo/api/tests"

# Run the typical tests, skipping tests marked to be skipped.
test:
    {{ PYTEST }} {{ PYTEST_SKIP }} {{ PYTEST_OPTS }}

# Run only the API tests.
test-api:
    {{ PYTEST }} {{ PYTEST_SKIP }} {{ PYTEST_OPTS }} {{ TEST_API_PATH }}

# Run all tests regardless of marks. This can be very slow.
test-all:
    {{ PYTEST }}

# Run only necessary tests given the changes in the code (pytest-testmon).
test-changes:
    {{ PYTEST }} --testmon

# Rerun the last failures only.
test-failures:
    {{ PYTEST }} --lf {{ PYTEST_SKIP }} {{ PYTEST_OPTS }}

# Run the web UI unit tests (vitest).
test-webui:
    cd webui && npx vitest run --config vitest.config.ts

# Run all tests (Python + WebUI).
test-everything: test test-webui

# Run the web-API and web-GUI for local development.
fullstack:
    python run_fullstack.py

# Serve docs locally (fast rebuild).
docs-fast:
    mkdocs serve -f mkdocs.yml

# Serve docs locally (ReadTheDocs config).
docs-rtd:
    mkdocs serve -f mkdocs.rtd.yml

# Run pre-commit hooks on staged files.
lint:
    pre-commit run

# run pre-commit hooks on all files.
ling-all:
    pre-commit run --all-files
