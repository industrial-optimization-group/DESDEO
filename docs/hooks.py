"""MkDocs hooks for fetching pre-run notebooks from GitHub before the build."""

import urllib.request
from pathlib import Path

_NOTEBOOKS = {
    "explanation/scenarios.ipynb": (
        "https://raw.githubusercontent.com/industrial-optimization-group"
        "/DESDEO/master/docs/explanation/scenarios.ipynb"
    ),
}


def on_pre_build(config, **kwargs):
    """Fetch pre-run notebooks from GitHub master so mkdocs-jupyter can render them without executing."""
    docs_dir = Path(config["docs_dir"])
    for rel_path, url in _NOTEBOOKS.items():
        dest = docs_dir / rel_path
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as e:
            print(f"Warning: could not fetch {rel_path} from GitHub ({e}). Using local copy if present.")
