#!/usr/bin/env python3
"""Print the app's OpenAPI schema to stdout.

The frontend's TypeScript API types are generated from this (`just types`), so
the Pydantic schemas are the single source of truth for the wire contract and
`client.ts` never hand-mirrors them.

Imports the app rather than hitting a running server, so it works in CI.

Run via:  just types
          cd backend && uv run python scripts/dump_openapi.py
"""

import json
import sys
from pathlib import Path

# Allow importing from the app package (script lives in backend/scripts/)
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def main() -> None:
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
