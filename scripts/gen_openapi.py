"""Generate the OpenAPI JSON spec from the FastAPI app."""

import json
from pathlib import Path

from desdeo.api.app import app

output = Path("docs/web_api/openapi.json")
output.write_text(json.dumps(app.openapi(), indent=2))
print(f"OpenAPI spec written to {output} ({len(output.read_text())} bytes)")
