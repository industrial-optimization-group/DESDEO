from pathlib import Path
import json
import sys

try:
    from desdeo.api.app import app
except ModuleNotFoundError as e:
    print(f"Missing dependency: {e.name}")
    print(
    "Install the required web dependencies "
    "(uv sync --group web or pip install -e .[web])."
    )
    sys.exit(1)


def main():
    output = Path("docs/web_api/openapi.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(app.openapi(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Generated {output}")


if __name__ == "__main__":
    main()