#!/usr/bin/env python3
"""LIVE end-to-end pipeline demo: parse → approve → local-check → REAL Polygon
upload → REAL package build → link.

Uses the eqpairs fixture as stand-in "generated artifacts" (in production the
generation agents write these). Creates ONE real problem with a unique name.

Run:  python3 scripts/demo_pipeline.py
Reads .env (secrets never printed).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
FIXTURE = REPO / "tests" / "fixtures" / "eqpairs"


def load_dotenv(path: Path) -> None:
    secret = {"POLYGON_API_KEY", "POLYGON_API_SECRET"}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            os.environ.setdefault(k, v.strip() if k in secret else v.split("#", 1)[0].strip())


load_dotenv(REPO / ".env")

from orchestrator import parse_create_problem, Orchestrator, PolygonUploader, StateStore
from polygon_client.auth import PolygonSession

UNIQUE = f"eqpairs-demo-{int(time.time())}"

INPUT = f"""/create-problem
name:          {UNIQUE}
statement:     Count pairs (i<j) with a_i == a_j, summed over t test cases.
solution:      Frequency map, sum C(v,2) per value. O(n) per test.
constraints:   1 <= t <= 10, 1 <= n <= 10^5, 1 <= a_i <= 10^9
time_limit:    100ms
answer_unique: yes
sample tests:
  Input:  2
          4
          1 2 2 3
          3
          5 5 5
  Output: 1
          3
"""


def copy_fixture(problem_dir: Path, name: str):
    for item in ("validator.cpp", "script.txt"):
        shutil.copy(FIXTURE / item, problem_dir / item)
    for sub in ("generators", "solutions", "samples", "validator_stress"):
        shutil.copytree(FIXTURE / sub, problem_dir / sub, dirs_exist_ok=True)
    meta = json.loads((FIXTURE / "meta.json").read_text())
    meta["name"] = name  # unique per run
    (problem_dir / "meta.json").write_text(json.dumps(meta, indent=2))


def main() -> int:
    ci = parse_create_problem(INPUT)
    session = PolygonSession.from_env()
    uploader = PolygonUploader(session)
    root = REPO / "problems"

    def runner(agent_name, payload):
        pdir = root / ci.name
        if agent_name == "spec-agent":
            (pdir / "PROBLEM_SPEC.md").write_text(f"# PROBLEM_SPEC: {ci.name}\n(demo)\n")
        else:
            copy_fixture(pdir, ci.name)
        return "ok"

    orch = Orchestrator(problems_root=root, runner=runner, uploader=uploader)

    print(f"→ start ({ci.name})")
    orch.start(ci)
    print("  state:", StateStore.load(orch.problem_dir).state.value)

    print("→ approve")
    orch.approve()

    print("→ generate (copy fixture artifacts)")
    orch.generate()

    print("→ local self-check")
    report = orch.local_check()
    print("  " + report.text().splitlines()[0])
    if not report.ok:
        print(report.text()); return 1

    print("→ upload (REAL Polygon, tab-by-tab)")
    created = orch.upload()
    print(f"  created id={created['id']} owner={created['owner']}")

    print("→ invocations (local harness)")
    orch.run_invocations()

    print("→ finalize (REAL buildPackage, may take ~1 min)")
    result = orch.finalize(created)

    print("\n" + result)
    print(f"\n(demo problem id {created['id']} left on account — delete from UI)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
