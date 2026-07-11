#!/usr/bin/env python3
"""End-to-end upload-path dry run against a real Polygon account.

Proves the full pipeline on one trivial problem (a+b):
  create → updateWorkingCopy → saveStatement → saveFile(validator)+setValidator
  → setChecker(std) → saveSolution(MA) → saveTest×2 → commitChanges
  → buildPackage → poll packages → construct link.

Run:  python3 scripts/e2e_dry_run.py

Reads .env (secrets never printed). Leaves one real problem on the account;
its id + link are printed at the end.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def load_dotenv(path: Path) -> None:
    if not path.exists():
        print(f"ERROR: {path} not found."); sys.exit(2)
    secret_keys = {"POLYGON_API_KEY", "POLYGON_API_SECRET"}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip() if k in secret_keys else v.split("#", 1)[0].strip()
        os.environ.setdefault(k, v)


load_dotenv(REPO / ".env")

from polygon_client.auth import PolygonSession, PolygonAPIError  # noqa: E402
from polygon_client import methods as m  # noqa: E402

VALIDATOR_CPP = r"""#include "testlib.h"
int main(int argc, char* argv[]) {
    registerValidation(argc, argv);
    inf.readInt(1, 1000000000, "a");
    inf.readSpace();
    inf.readInt(1, 1000000000, "b");
    inf.readEoln();
    inf.readEof();
    return 0;
}
"""

MAIN_CPP = r"""#include <bits/stdc++.h>
using namespace std;
int main() {
    long long a, b;
    cin >> a >> b;
    cout << a + b << '\n';
    return 0;
}
"""


def step(label, fn):
    try:
        result = fn()
        print(f"✅ {label}")
        return result
    except PolygonAPIError as exc:
        print(f"❌ {label}: {exc}")
        raise


def main() -> int:
    s = PolygonSession.from_env()
    name = f"e2e-aplusb-{int(time.time())}"

    created = step(f"create '{name}'", lambda: m.create_problem(s, name))
    pid, owner = created["id"], created["owner"]
    print(f"   id={pid} owner={owner}")

    step("updateWorkingCopy", lambda: m.update_working_copy(s, pid))

    step("saveStatement", lambda: m.save_statement(
        s, pid,
        name="Sum of Two Numbers",
        legend="Given two integers $a$ and $b$, output their sum.",
        input_="A single line with two integers $a$ and $b$ "
               "($1 \\le a, b \\le 10^9$).",
        output="Print a single integer — the value $a + b$.",
        notes="",
    ))

    step("saveFile validator.cpp", lambda: m.save_file(
        s, pid, type_="source", name="validator.cpp", source=VALIDATOR_CPP))
    step("setValidator", lambda: m.set_validator(s, pid, "validator.cpp"))

    step("setChecker std::ncmp.cpp", lambda: m.set_checker(s, pid, "std::ncmp.cpp"))

    step("saveSolution main.cpp (MA)", lambda: m.save_solution(
        s, pid, "main.cpp", MAIN_CPP, "MA"))

    step("saveTest #1 (sample)", lambda: m.save_test(
        s, pid, "tests", 1, "3 5\n", use_in_statements=True))
    step("saveTest #2", lambda: m.save_test(
        s, pid, "tests", 2, "1000000000 1000000000\n"))

    step("commitChanges", lambda: m.commit_changes(s, pid, "e2e: full problem"))

    step("buildPackage(full, verify)", lambda: m.build_package(
        s, pid, full=True, verify=True))

    # Poll packages until the newest is READY / FAILED.
    print("   polling package build...", end="", flush=True)
    final_state = None
    for _ in range(40):  # up to ~2 min
        time.sleep(3)
        try:
            pkgs = m.packages(s, pid) or []
        except PolygonAPIError:
            print("!", end="", flush=True); continue
        if not pkgs:
            print(".", end="", flush=True); continue
        newest = max(pkgs, key=lambda p: p.get("id", 0))
        state = newest.get("state")
        print(f"[{state}]", end="", flush=True)
        if state in ("READY", "FAILED"):
            final_state = state
            break
    print()
    if final_state == "READY":
        print(f"✅ package READY")
    elif final_state == "FAILED":
        print(f"❌ package FAILED — check the Polygon UI package log")
    else:
        print(f"⚠️  package still building/unknown after poll window")

    link = m.problem_url(owner, name)
    print(f"\n🔗 {link}")
    print(f"   (problem id {pid} left on account — keep or delete from UI)")
    return 0 if final_state == "READY" else 1


if __name__ == "__main__":
    sys.exit(main())
