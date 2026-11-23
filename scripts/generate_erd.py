"""Generate the database ER diagram for the documentation."""

from pathlib import Path
import sys

try:
    from eralchemy import render_er
except ModuleNotFoundError:
    print(
        "Missing dependency: eralchemy\n"
        "Install the tools dependencies before generating the ER diagram."
    )
    sys.exit(1)

from desdeo.api.db import Base
import desdeo.api.db_models  # Registers all SQLAlchemy tables.


def main() -> None:
    """Generate the database ER diagram."""
    output = Path("docs/web_api/schema.svg")
    output.parent.mkdir(parents=True, exist_ok=True)

    render_er(Base.metadata, str(output))

    print(f"Generated {output}")


if __name__ == "__main__":
    main()