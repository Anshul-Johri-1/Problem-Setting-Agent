"""orchestrator/cli.py tests — the single sanctioned entrypoint for anything
live-touching (§ security incident, 2026-07-11: an agent bypassed every
guardrail by driving Orchestrator/PolygonUploader directly instead of through
this CLI). These tests never touch real Polygon — `finish` is only exercised
on a hand-forged (never-approved) state, which must refuse before any network
call, matching the exact observed bypass pattern.

Run: python3 tests/test_cli.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.state import StateStore, State

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "eqpairs"


def _spec_input(name: str) -> dict:
    return {
        "name": name, "statement": "test", "solution": "test",
        "constraints": "1<=n<=10",
        "samples": [{"input": "1\n1\n1\n", "output": "0\n"}],
        "time_limit": None, "memory_limit": None, "answer_unique": None,
        "num_tests": None, "num_solutions": None, "num_generators": None,
    }


def _run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "orchestrator.cli", "--root", str(root), *args],
        cwd=REPO, capture_output=True, text=True,
    )


def test_approve_before_awaiting_approval_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        problem = root / "p1"
        problem.mkdir()
        (problem / "spec_input.json").write_text(json.dumps(_spec_input("p1")))
        StateStore.init(problem, "p1")  # DRAFTING_SPEC

        r = _run_cli(root, "approve", "p1")
        assert r.returncode != 0
        assert "illegal transition" in r.stdout


def test_approve_then_begin_generation_materializes_samples():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        problem = root / "p2"
        problem.mkdir()
        (problem / "spec_input.json").write_text(json.dumps(_spec_input("p2")))
        store = StateStore.init(problem, "p2")
        store.transition(State.AWAITING_APPROVAL, "spec drafted (test)")

        r1 = _run_cli(root, "approve", "p2")
        assert r1.returncode == 0, r1.stdout

        r2 = _run_cli(root, "begin-generation", "p2")
        assert r2.returncode == 0, r2.stdout
        assert (problem / "samples" / "sample-01.txt").read_text() == "1\n1\n1\n"
        assert (problem / "samples_expected" / "sample-01.txt").read_text() == "0\n"
        assert StateStore.load(problem).state == State.GENERATING_ARTIFACTS


def test_finish_refuses_on_hand_forged_state_before_any_network_call():
    """Reproduces the exact observed bypass: state.state = X; state._write()
    instead of calling approve(). Populates real, locally-green fixture
    content so the refusal is proven to come from the approval check
    specifically, not from missing artifacts."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        problem = root / "p3"
        problem.mkdir()
        (problem / "spec_input.json").write_text(json.dumps(_spec_input("p3")))
        store = StateStore.init(problem, "p3")
        store.state = State.GENERATING_ARTIFACTS  # forged, no transition() call
        store._write()

        for item in ("meta.json", "validator.cpp", "script.txt", "PROBLEM_SPEC.md"):
            shutil.copy(FIXTURE / item, problem / item)
        for sub in ("generators", "solutions", "samples", "validator_stress", "validator_valid"):
            shutil.copytree(FIXTURE / sub, problem / sub, dirs_exist_ok=True)

        r = _run_cli(root, "finish", "p3")
        assert r.returncode != 0
        assert "no genuine AWAITING_APPROVAL" in r.stdout


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nAll {len(fns)} CLI tests passed.")
