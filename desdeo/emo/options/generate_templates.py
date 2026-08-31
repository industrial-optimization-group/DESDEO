"""Regenerate the serialized EMO option templates under `datasets/emoTemplates`.

Run with::

    python -m desdeo.emo.options.generate_templates

The templates are read back at runtime by `desdeo.api.routers.emo.get_templates`, so regenerate
them whenever the option models change.

Note:
    This lives in its own module rather than under `if __name__ == "__main__":` in
    `algorithms.py`. `desdeo/emo/__init__.py` imports `algorithms` eagerly, so running that module
    with `-m` would import it once as `desdeo.emo.options.algorithms` and then execute it a second
    time as `__main__`, which `runpy` reports as::

        RuntimeWarning: 'desdeo.emo.options.algorithms' found in sys.modules after import of
        package 'desdeo.emo.options', but prior to execution of ...; this may result in
        unpredictable behaviour

    Nothing imports this module, so executing it with `-m` runs it exactly once.
"""

import json
from collections.abc import Callable
from pathlib import Path

from desdeo.emo.options.algorithms import (
    ibea_mixed_integer_options,
    ibea_options,
    nsga3_mixed_integer_options,
    nsga3_options,
    rvea_mixed_integer_options,
    rvea_options,
    xlemoo_options,
)
from desdeo.emo.options.templates import EMOOptions

TEMPLATES: dict[str, Callable[[], EMOOptions]] = {
    "rvea": rvea_options,
    "nsga3": nsga3_options,
    "ibea": ibea_options,
    "rvea_mixed_integer": rvea_mixed_integer_options,
    "nsga3_mixed_integer": nsga3_mixed_integer_options,
    "ibea_mixed_integer": ibea_mixed_integer_options,
    "xlemoo": xlemoo_options,
}
"""The templates to dump, keyed by the file name they are written to."""

DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "datasets" / "emoTemplates"
"""Repository path the templates are written to, i.e. `<repo root>/datasets/emoTemplates`."""


def generate_templates(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Write every option template, and the option schema, as JSON.

    Args:
        output_dir (Path): the directory to write to. Created if it does not exist.
            Defaults to `datasets/emoTemplates` in the repository.

    Returns:
        list[Path]: the files that were written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for name, build_options in TEMPLATES.items():
        path = output_dir / f"{name}.json"
        _dump(build_options().model_dump(), path)
        written.append(path)

    schema_path = output_dir / "emoOptionsSchema.json"
    _dump(EMOOptions.model_json_schema(), schema_path)
    written.append(schema_path)

    return written


def _dump(data: dict, path: Path) -> None:
    """Write `data` as indented JSON, ending with a newline.

    The trailing newline keeps the output stable under the `end-of-file-fixer` pre-commit hook,
    which would otherwise rewrite every file after each regeneration.
    """
    with path.open("w") as file:
        json.dump(data, file, indent=4)
        file.write("\n")


if __name__ == "__main__":
    for path in generate_templates():
        print(f"wrote {path}")  # noqa: T201
