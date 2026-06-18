"""Generate the database ER diagram SVG from SQLAlchemy metadata."""

from pathlib import Path

from sqlalchemy_schemadisplay import create_schema_graph

from desdeo.api.db import engine, Base
import desdeo.api.db_models  # noqa: F401 — register all table models

output = Path("docs/web_api/schema.svg")
graph = create_schema_graph(
    engine=engine,
    metadata=Base.metadata,
    show_datatypes=True,
    show_indexes=False,
    rankdir="LR",
    concentrate=False,
)
graph.write_svg(str(output))
print(f"ER diagram written to {output} ({output.stat().st_size} bytes)")
