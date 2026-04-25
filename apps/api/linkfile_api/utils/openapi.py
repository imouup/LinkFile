from __future__ import annotations

import json
import sys
from pathlib import Path

from linkfile_api.main import app


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
