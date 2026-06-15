# Contributing to DESDEO

Thank you for your interest in contributing to DESDEO! Contributions of all
kinds are welcome: bug reports, bug fixes, new features, new interactive
methods, documentation improvements, and more.

This file is a short overview. The full, detailed contribution guide lives in
the documentation:

**[Contributing to DESDEO](https://desdeo.readthedocs.io/en/latest/tutorials/contributing/)**
(source: [`docs/tutorials/contributing.md`](docs/tutorials/contributing.md))

The full guide covers, step by step: installing the required software,
setting up a development environment with `uv`, the fork, branch, and pull
request workflow, code style and linting (`ruff`, `mypy`), running the test
suite, pre-commit hooks, docstring conventions, and building the documentation.

## Quick start for contributors

1. Fork the repository and clone your fork.
2. Set up a development environment and install all dependencies:
   ```bash
   uv sync
   ```
   (`uv` also installs the `just` task runner used below.)
3. Create a feature branch off `master`.
4. Make your changes, keeping commits focused and well described.
5. Run the test suite:
   ```bash
   just test
   ```
   Run `just --list` to see all available recipes.
6. Push your branch and open a pull request against `master`.

## Reporting issues and getting help

- **Found a bug?** Open a [bug report](https://github.com/industrial-optimization-group/DESDEO/issues/new/choose).
- **Have an idea or feature request?** Open an
  [idea discussion](https://github.com/industrial-optimization-group/DESDEO/issues/new/choose).
- **Need help or want to discuss?** Join our
  [Discord server](https://discord.gg/uGCEgQTJyY).

## Code of Conduct

By participating in this project you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).
