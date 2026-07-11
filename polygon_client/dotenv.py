"""The ONE canonical `.env` loader in this repo.

Every script that needed this used to carry its own copy-pasted version —
which meant every copy was also a ready-made template for a new ad hoc script
to construct a live, authenticated PolygonSession. Consolidating to a single
implementation, imported everywhere, removes that specific incentive (see
`.claude/GUARDRAILS.md`): `orchestrator/cli.py` is the only place that should
ever call this in a way that leads to a real Polygon call.
"""

from __future__ import annotations

import os
from pathlib import Path

_SECRET_KEYS = {"POLYGON_API_KEY", "POLYGON_API_SECRET"}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip() if key in _SECRET_KEYS else val.split("#", 1)[0].strip()
        os.environ.setdefault(key, val)
