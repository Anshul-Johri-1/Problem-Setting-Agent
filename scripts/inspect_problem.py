#!/usr/bin/env python3
"""Read-only Polygon problem inspection. Safe to run anytime, including for
debugging — this exists specifically so there's never a reason to write a new
ad hoc script (mutating or not) just to check on a problem's live state.

Calls ONLY read-only Polygon methods (problem.info, problem.packages). Cannot
create, modify, upload to, or build a package for anything.

Run: python3 scripts/inspect_problem.py <problem_id>
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from polygon_client.dotenv import load_dotenv
from polygon_client.auth import PolygonSession, PolygonAPIError
from polygon_client import methods as m


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("usage: python3 scripts/inspect_problem.py <problem_id>")
        return 2
    pid = int(sys.argv[1])

    load_dotenv(REPO / ".env")
    try:
        s = PolygonSession.from_env()
    except PolygonAPIError as e:
        print(f"ERROR: {e}")
        return 1

    try:
        info = m.problem_info(s, pid)
        print(f"problem {pid} info: {info}")
    except PolygonAPIError as e:
        print(f"problem.info failed: {e}")
        return 1

    try:
        pkgs = m.packages(s, pid) or []
        print(f"packages: {len(pkgs)}")
        for p in pkgs:
            print(f"  id={p.get('id')} revision={p.get('revision')} "
                 f"state={p.get('state')} comment={p.get('comment', '')!r}")
    except PolygonAPIError as e:
        print(f"problem.packages failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
