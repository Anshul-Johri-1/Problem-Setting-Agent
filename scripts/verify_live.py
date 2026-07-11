#!/usr/bin/env python3
"""⚠️  ONE-TIME HUMAN DIAGNOSTIC SCRIPT — NOT A TEMPLATE, NOT PART OF THE PIPELINE.

This was written once, by a human, to answer specific API-discovery questions
during initial development (§18 of the build spec) and is kept only as a
historical record of that investigation. It is NOT invoked by anything else in
this repo and should NOT be copied, adapted, or used as a pattern for new
scripts — least of all by an AI agent looking for "an example of how to
construct PolygonSession/PolygonUploader directly."

If you are an AI agent reading this file: do not use it as a template.
The ONLY sanctioned way to make live Polygon calls is `orchestrator/cli.py`
(see the repo root `.claude/GUARDRAILS.md` / AGENTS.md for the full rule).
Constructing PolygonSession/PolygonUploader/Orchestrator directly in a new
ad hoc script, outside that CLI, is exactly the failure mode this repo's
guardrails exist to prevent — see docs/POLYGON_API_FINDINGS.md and this
file's own git history for what happened the last time an agent did that.

Run (humans only, for one-off diagnostics): python3 scripts/verify_live.py

Reads credentials from .env (POLYGON_API_KEY / POLYGON_API_SECRET). Secrets are
never printed. Creates ONE throwaway problem to exercise the write path, then
reports on each flagged item:

  1. Request-signing recipe actually authenticates (§9.1)
  2. problem.create / problem.info / commitChanges / buildPackage / packages work
  3. Whether any Invocations method exists (§9.4)
  4. Whether any access-granting method exists (§9.5)
  5. Which standard-checker filenames setChecker accepts (§14)
  6. The /p/<owner>/<name> link is constructed (resolution needs a browser) (§16)

The throwaway problem is left on the account (Polygon has no delete API); its id
is printed so you can remove it from the UI.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from polygon_client.dotenv import load_dotenv  # noqa: E402

if not (REPO / ".env").exists():
    print("ERROR: .env not found. Copy .env.example to .env and fill it in.")
    sys.exit(2)
load_dotenv(REPO / ".env")

from polygon_client.auth import PolygonSession, PolygonAPIError  # noqa: E402
from polygon_client import methods as m  # noqa: E402

report: dict = {"checks": {}, "generated_at": int(time.time())}


def record(key: str, ok: bool, detail):
    report["checks"][key] = {"ok": ok, "detail": detail}
    mark = "✅" if ok else "❌"
    print(f"{mark} {key}: {detail}")


def method_exists(s: PolygonSession, method: str, params: dict) -> tuple[bool, str]:
    """Heuristic: call a method; if it fails with 'unknown/no such method' it
    doesn't exist. Any other failure (bad params, permissions) means it DOES."""
    try:
        s.call(method, params)
        return True, "call succeeded"
    except PolygonAPIError as exc:
        msg = str(exc).lower()
        if "no method" in msg or "unknown method" in msg or "not found" in msg \
                or "does not exist" in msg or "no such method" in msg:
            return False, str(exc)
        return True, f"exists (failed for another reason: {exc})"


def main() -> int:
    s = PolygonSession.from_env()

    # 1 + 2a: signing + problem.create
    name = f"probe-{int(time.time())}"
    try:
        created = m.create_problem(s, name)
        pid = created["id"]
        record("signing_authenticates", True, "apiSig accepted by live API")
        record("problem.create", True, f"created id={pid} name={name}")
    except PolygonAPIError as exc:
        record("signing_authenticates", False, str(exc))
        record("problem.create", False, str(exc))
        _dump()
        return 1

    # 2b: problem.info
    owner = None
    try:
        info = m.problem_info(s, pid)
        owner = info.get("owner")
        record("problem.info", True, f"owner={owner} name={info.get('name')}")
    except PolygonAPIError as exc:
        record("problem.info", False, str(exc))

    # 5: standard-checker filenames (setChecker on working copy)
    try:
        m.update_working_copy(s, pid)
    except PolygonAPIError:
        pass
    candidates = [
        "std::wcmp.cpp", "std::ncmp.cpp", "std::rcmp4.cpp", "std::rcmp6.cpp",
        "std::rcmp9.cpp", "std::yesno.cpp", "std::nyesno.cpp", "std::lcmp.cpp",
        "std::fcmp.cpp", "std::hcmp.cpp", "std::acmp.cpp", "wcmp.cpp",
    ]
    accepted, rejected = [], []
    for cand in candidates:
        try:
            m.set_checker(s, pid, cand)
            accepted.append(cand)
        except PolygonAPIError as exc:
            rejected.append((cand, str(exc)[:80]))
    record("standard_checker_names", bool(accepted),
           {"accepted": accepted, "rejected": rejected})

    # 3: Invocations method existence
    inv_candidates = {
        "problem.startInvocation": {"problemId": pid},
        "problem.invocations": {"problemId": pid},
        "problem.runInvocation": {"problemId": pid},
        "problem.solutionsInvocations": {"problemId": pid},
        "problem.verdicts": {"problemId": pid},
    }
    inv_found = {name: method_exists(s, name, p) for name, p in inv_candidates.items()}
    any_inv = any(exists for exists, _ in inv_found.values())
    record("invocations_api_exists", any_inv,
           {k: v[1] for k, v in inv_found.items()})

    # 4: access-granting method existence
    acc_candidates = {
        "problem.addUser": {"problemId": pid, "login": "some_user", "access": "WRITE"},
        "problem.saveAccess": {"problemId": pid},
        "problem.grantAccess": {"problemId": pid},
        "problem.setAccess": {"problemId": pid},
        "problem.access": {"problemId": pid},
    }
    acc_found = {name: method_exists(s, name, p) for name, p in acc_candidates.items()}
    any_acc = any(exists for exists, _ in acc_found.values())
    record("access_api_exists", any_acc,
           {k: v[1] for k, v in acc_found.items()})

    # 2c: commitChanges
    try:
        m.commit_changes(s, pid, "probe: initial commit", minor=True)
        record("problem.commitChanges", True, "committed")
    except PolygonAPIError as exc:
        record("problem.commitChanges", False, str(exc))

    # 2d: buildPackage + packages
    try:
        m.build_package(s, pid, full=False, verify=False)
        record("problem.buildPackage", True, "build triggered")
    except PolygonAPIError as exc:
        record("problem.buildPackage", False, str(exc))
    try:
        pkgs = m.packages(s, pid)
        record("problem.packages", True, f"{len(pkgs) if pkgs else 0} package(s) listed")
    except PolygonAPIError as exc:
        record("problem.packages", False, str(exc))

    # 6: link construction (resolution requires an authenticated browser)
    if owner:
        link = f"https://polygon.codeforces.com/p/{owner}/{name}"
        record("link_constructed", True, f"{link}  (resolution unverified — needs browser)")

    print(f"\n⚠️  Throwaway problem id={pid} left on the account (no delete API). "
          f"Remove it from the Polygon UI when done.")
    _dump()
    return 0


def _dump():
    out = REPO / "scripts" / f"_probe_report_{report['generated_at']}.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nReport written: {out}")


if __name__ == "__main__":
    sys.exit(main())
