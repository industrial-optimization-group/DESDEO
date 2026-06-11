"""Project-wide pytest configuration.

This root conftest applies to every test path declared in ``pyproject.toml``
(``testpaths = ["tests", "desdeo/api/tests"]``).
"""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip ``fixme``-marked tests when ``TESTMON_SKIP_FIXME`` is set.

    ``just test-changes`` relies on pytest-testmon, which cannot be combined
    with a ``-m`` mark expression (doing so stops testmon from saving a stable
    baseline, so it silently reruns the whole suite). We therefore cannot pass
    ``-m "not fixme"`` there. Instead, the recipe sets ``TESTMON_SKIP_FIXME=1``
    and this hook converts the would-be deselection into a skip, which testmon
    tolerates. Other recipes (``just test``, ``just test-all``) are unaffected.
    """
    if not os.environ.get("TESTMON_SKIP_FIXME"):
        return

    skip_fixme = pytest.mark.skip(reason="fixme test skipped via TESTMON_SKIP_FIXME")
    for item in items:
        if "fixme" in item.keywords:
            item.add_marker(skip_fixme)
