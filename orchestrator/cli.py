#!/usr/bin/env python3
"""THE single sanctioned entrypoint for anything that touches live Polygon.

Every AI agent driving this repo — regardless of which model or tool is
running it — MUST use this CLI for the mechanical/live-touching parts of the
pipeline. Do not construct PolygonSession/PolygonUploader/Orchestrator
directly in a new ad hoc script. See `.claude/GUARDRAILS.md` for the full
rule and why it exists (short version: an agent did exactly that once, and it
uploaded unverified content to two real Polygon problems under fabricated
"local check passed" data — see docs/POLYGON_API_FINDINGS.md).

What this CLI does NOT do, on purpose: draft PROBLEM_SPEC.md, or write
validator/solution/generator/statement content. That's genuine reasoning work
only an actual model can do — no script should try to automate it, and this
one doesn't pretend to. Write those files yourself, per the relevant
`.claude/agents/*.md` file's instructions, THEN use this CLI for everything
that follows.

There is no local-check command. Nothing in this repo compiles or runs any
solution/generator/validator/checker locally — Polygon's own
`buildPackage(verify=True)` is the one verification gate (§9.4: Polygon has no
invocations API, confirmed live, so its build-failure comment is the only
diagnostic there is; see orchestrator/reviewer.py). `finish` triggers it.

Commands:
    status <name>             Read-only. Print current state + full audit
                               trail. Always safe — reach for this instead of
                               writing a one-off inspection script.
    approve <name>             Record a genuine human approval. Call this ONLY
                               after the human has unambiguously approved
                               PROBLEM_SPEC.md in the conversation — never
                               speculatively, never to "see what happens."
    begin-generation <name>   Transition to GENERATING_ARTIFACTS and
                               materialize samples/+samples_expected/ from
                               spec_input.json. Call this AFTER approve(),
                               BEFORE you write/dispatch the actual generation
                               content (validator.cpp, solutions/, etc.).
    finish <name>             The ONLY command that touches live Polygon:
                               upload (idempotent — safe to call again after a
                               patch) -> buildPackage(verify=True) -> sample
                               verify -> finalize. On a Polygon build failure
                               it halts and prints the diagnostic (state +
                               comment) instead of a partial success; if the
                               comment doesn't implicate a reference solution,
                               patch the responsible artifact (reviewer-agent
                               routes it) and simply re-run `finish` — it will
                               not re-create the problem or lose already-good
                               tabs. Refuses outright if `approve` was never
                               genuinely called for this problem — checked
                               against the audit trail, not just the current
                               state value.

All commands read credentials from .env via polygon_client.dotenv — nothing
else in this repo should load .env for a live call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from orchestrator.state import StateStore, State, InvalidTransition, UnapprovedUploadError
from orchestrator.input_parse import CreateProblemInput, SampleTest
from orchestrator.pipeline import Orchestrator, PipelineHalt, BuildFailure
from orchestrator.uploader import PolygonUploader
from orchestrator.gate import GateError
from polygon_client.auth import PolygonSession
from polygon_client.dotenv import load_dotenv


def _problem_dir(root: Path, name: str) -> Path:
    d = root / name
    if not (d / "state.json").exists():
        print(f"ERROR: {d}/state.json not found. This problem was never "
             f"initialized (no spec-agent has run for it yet).")
        sys.exit(2)
    return d


def _load_create_input(problem_dir: Path) -> CreateProblemInput:
    """Reconstruct the original /create-problem input from spec_input.json
    (written once, at Stage 0, by Orchestrator.start()). This CLI never
    re-parses or re-derives it — it's read verbatim."""
    data = json.loads((problem_dir / "spec_input.json").read_text())
    samples = [SampleTest(**s) for s in data.get("samples", [])]
    fields = {k: v for k, v in data.items() if k != "samples"}
    return CreateProblemInput(samples=samples, **fields)


def _no_creative_work_runner(agent_name: str, payload: dict):
    """Passed to Orchestrator only where it's structurally guaranteed never to
    be called (this CLI never invokes generate() or start()). If this ever
    fires, something is wrong — fail loudly instead of silently no-opping."""
    raise RuntimeError(
        f"cli.py's runner was invoked for '{agent_name}' — this should be "
        f"structurally impossible; this CLI never dispatches subagents. "
        f"Generation/spec-drafting must be done by the calling agent directly, "
        f"not through this CLI.")


def cmd_status(args) -> int:
    d = _problem_dir(args.root, args.name)
    store = StateStore.load(d)
    print(f"state: {store.state.value}")
    print(f"problem_id: {store.problem_id}")
    print(f"retry_count: {store.retry_count}")
    print("history:")
    for h in store.history:
        print(f"  {h.to_dict()['iso']}  {h.from_state} -> {h.to_state}  ({h.summary})")
    return 0


def cmd_approve(args) -> int:
    d = _problem_dir(args.root, args.name)
    store = StateStore.load(d)
    try:
        store.transition(State.APPROVED, "human approved (recorded via orchestrator.cli approve)")
    except InvalidTransition as e:
        print(f"ERROR: {e}\n(current state: {store.state.value} — approve() is only "
             f"legal from AWAITING_APPROVAL)")
        return 1
    print(f"✅ recorded genuine approval for '{args.name}'")
    return 0


def cmd_begin_generation(args) -> int:
    d = _problem_dir(args.root, args.name)
    ci = _load_create_input(d)
    # No uploader is constructed here on purpose: this command never touches
    # Polygon, only state.json + local files, so there is nothing to gate.
    orch = Orchestrator(problems_root=args.root, runner=_no_creative_work_runner,
                        uploader=None, create_input=ci)
    try:
        store = StateStore.load(d)
        from orchestrator.gate import assert_can_dispatch
        assert_can_dispatch("solutions-agent", store.state)
        store.transition(State.GENERATING_ARTIFACTS, "generating artifacts (via orchestrator.cli)")
        orch._materialize_samples()
    except (InvalidTransition, GateError) as e:
        print(f"ERROR: {e}")
        return 1
    print(f"✅ '{args.name}' is now GENERATING_ARTIFACTS; samples/ and "
         f"samples_expected/ materialized. Write validator.cpp, solutions/, "
         f"generators/, script.txt, statement.json, meta.json yourself now, "
         f"then run `finish`.")
    return 0


def cmd_finish(args) -> int:
    d = _problem_dir(args.root, args.name)
    ci = _load_create_input(d)

    load_dotenv(REPO / ".env")
    session = PolygonSession.from_env()
    uploader = PolygonUploader(session, d)  # re-verifies approval on every call

    orch = Orchestrator(problems_root=args.root, runner=_no_creative_work_runner,
                        uploader=uploader, create_input=ci)
    try:
        result = orch.run_after_approval()
    except BuildFailure as e:
        print(f"❌ HALTED (not a partial success) — Polygon build {e.result.state}:\n"
             f"{e.result.comment or '(no comment)'}\n\n"
             f"Patch the artifact this names (reviewer-agent routes it — see "
             f"tutorials/invocations.md), then re-run `finish`. `upload` is "
             f"idempotent: it will not re-create the problem or lose "
             f"already-uploaded tabs.")
        return 1
    except (PipelineHalt, UnapprovedUploadError, GateError) as e:
        print(f"❌ HALTED (not a partial success):\n{e}")
        return 1
    print(result)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="orchestrator.cli", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO / "problems",
                        help="problems root directory (default: ./problems)")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn in (("status", cmd_status), ("approve", cmd_approve),
                     ("begin-generation", cmd_begin_generation),
                     ("finish", cmd_finish)):
        p = sub.add_parser(name)
        p.add_argument("name", help="problem name (directory under --root)")
        p.set_defaults(func=fn)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
