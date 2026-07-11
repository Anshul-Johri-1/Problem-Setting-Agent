"""Tests for the structural approval gate (§1.1, §6) and state machine (§7).

Run: python3 -m pytest tests/test_gate.py -q   (or: python3 tests/test_gate.py)
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.state import State, StateStore, InvalidTransition
from orchestrator.gate import assert_can_dispatch, GateError
from orchestrator.dispatch import dispatch


GENERATION_AGENTS = ["statement-agent", "validator-agent", "checker-agent",
                     "solutions-agent", "generator-agent"]


def test_generation_agents_blocked_before_approval():
    for agent in GENERATION_AGENTS:
        for state in (State.DRAFTING_SPEC, State.AWAITING_APPROVAL):
            try:
                assert_can_dispatch(agent, state)
            except GateError:
                pass
            else:
                raise AssertionError(f"{agent} not blocked in {state}!")


def test_generation_agents_allowed_after_approval():
    for agent in GENERATION_AGENTS:
        assert_can_dispatch(agent, State.APPROVED)
        assert_can_dispatch(agent, State.GENERATING_ARTIFACTS)


def test_spec_agent_only_pre_approval():
    assert_can_dispatch("spec-agent", State.DRAFTING_SPEC)
    assert_can_dispatch("spec-agent", State.AWAITING_APPROVAL)
    try:
        assert_can_dispatch("spec-agent", State.GENERATING_ARTIFACTS)
    except GateError:
        pass
    else:
        raise AssertionError("spec-agent should not run post-approval")


def test_reviewer_only_during_building_package():
    assert_can_dispatch("reviewer-agent", State.BUILDING_PACKAGE)
    try:
        assert_can_dispatch("reviewer-agent", State.APPROVED)
    except GateError:
        pass
    else:
        raise AssertionError("reviewer-agent should only run during BUILDING_PACKAGE")


def test_dispatch_refuses_runner_when_gated():
    """The runner must NOT be called if the gate blocks — proves enforcement is
    upstream of any work."""
    with tempfile.TemporaryDirectory() as d:
        pd = Path(d)
        StateStore.init(pd, "demo")  # starts in DRAFTING_SPEC
        called = {"ran": False}

        def runner(agent, payload):
            called["ran"] = True
            return "should-not-happen"

        try:
            dispatch(pd, "validator-agent", {"spec": "x"}, runner)
        except GateError:
            pass
        else:
            raise AssertionError("dispatch should have raised GateError")
        assert called["ran"] is False, "runner ran despite gate block!"


def test_full_happy_path_transitions():
    with tempfile.TemporaryDirectory() as d:
        pd = Path(d)
        store = StateStore.init(pd, "demo")
        seq = [
            State.AWAITING_APPROVAL, State.APPROVED, State.GENERATING_ARTIFACTS,
            State.UPLOADING_STATEMENT, State.UPLOADING_VALIDATOR,
            State.UPLOADING_CHECKER, State.UPLOADING_TESTS,
            State.UPLOADING_SOLUTIONS, State.SETTING_LIMITS,
            State.FINAL_COMMIT, State.BUILDING_PACKAGE,
            State.SAMPLE_VERIFY, State.LINK_READY,
        ]
        for s in seq:
            store.transition(s, f"→ {s.value}")
        assert store.state == State.LINK_READY
        # reloaded state persists with full history
        reloaded = StateStore.load(pd)
        assert reloaded.state == State.LINK_READY
        assert len(reloaded.history) == len(seq) + 1  # + init entry


def test_illegal_transition_raises():
    with tempfile.TemporaryDirectory() as d:
        pd = Path(d)
        store = StateStore.init(pd, "demo")
        try:
            store.transition(State.LINK_READY, "skip everything")
        except InvalidTransition:
            pass
        else:
            raise AssertionError("illegal jump should raise")


def test_building_package_bounces_back_to_generating_artifacts():
    """A routable Polygon build failure re-enters generation for a targeted
    patch (§15) — there is no per-tab bounce target anymore since upload() is
    idempotent and just re-sends every tab."""
    with tempfile.TemporaryDirectory() as d:
        pd = Path(d)
        store = StateStore.init(pd, "demo")
        for s in (State.AWAITING_APPROVAL, State.APPROVED, State.GENERATING_ARTIFACTS,
                 State.UPLOADING_STATEMENT, State.UPLOADING_VALIDATOR,
                 State.UPLOADING_CHECKER, State.UPLOADING_TESTS,
                 State.UPLOADING_SOLUTIONS, State.SETTING_LIMITS,
                 State.FINAL_COMMIT, State.BUILDING_PACKAGE):
            store.transition(s, f"→ {s.value}")
        store.transition(State.GENERATING_ARTIFACTS, "Polygon build FAILED; targeted patch")
        assert store.state == State.GENERATING_ARTIFACTS
        # and back onto the upload path again
        store.transition(State.UPLOADING_STATEMENT, "re-upload after patch")
        assert store.state == State.UPLOADING_STATEMENT


def test_escalation_reachable_from_any_state():
    with tempfile.TemporaryDirectory() as d:
        pd = Path(d)
        store = StateStore.init(pd, "demo")
        store.transition(State.AWAITING_APPROVAL, "spec ready")
        store.transition(State.APPROVED, "approved")
        store.transition(State.ESCALATE_TO_HUMAN, "correct solution got WA")
        assert store.state == State.ESCALATE_TO_HUMAN


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nAll {len(fns)} tests passed.")
