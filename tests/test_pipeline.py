"""Pipeline driver tests (§5, §6, §7, §10, §11, §15).

Drives the full orchestrator with a fixture-backed runner (generation = copy the
eqpairs artifacts) and a RecordingUploader, so the whole pipeline runs end-to-end
WITHOUT touching Polygon. Also asserts the structural approval gate holds inside
the pipeline.

Run: python3 tests/test_pipeline.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import (parse_create_problem, InputError, Orchestrator,
                          RecordingUploader, GateError, State, StateStore,
                          PipelineHalt, BuildFailure)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "eqpairs"

SAMPLE_INPUT = """/create-problem
name:          eqpairs
statement:     Count pairs (i<j) with a_i == a_j, over t test cases.
solution:      Frequency map, sum C(v,2). O(n) per test.
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


def fixture_runner(agent_name: str, payload: dict):
    """Stand-in for LLM subagents: spec-agent writes a spec; generation agents
    copy the eqpairs fixture artifacts into the problem dir."""
    spec_dir = Path(payload.get("spec_dir") or payload.get("create_input", {}).get("_dir", ""))
    if agent_name == "spec-agent":
        # spec_dir isn't in payload for spec-agent; use the closure target below
        return "spec-written"
    return "artifacts-written"


def _copy_fixture_artifacts(problem_dir: Path):
    for item in ("meta.json", "validator.cpp", "script.txt", "PROBLEM_SPEC.md"):
        shutil.copy(FIXTURE / item, problem_dir / item)
    for sub in ("generators", "solutions", "samples", "validator_stress", "validator_valid"):
        shutil.copytree(FIXTURE / sub, problem_dir / sub, dirs_exist_ok=True)


def test_parse_valid():
    ci = parse_create_problem(SAMPLE_INPUT)
    assert ci.name == "eqpairs"
    assert ci.answer_unique == "yes"
    assert len(ci.samples) == 1
    assert ci.samples[0].output.strip().splitlines() == ["1", "3"]


def test_parse_rejects_bad_name():
    bad = SAMPLE_INPUT.replace("name:          eqpairs", "name:          eq_pairs")
    try:
        parse_create_problem(bad)
    except InputError:
        pass
    else:
        raise AssertionError("underscore name should be rejected")


def test_parse_optional_counts():
    with_counts = SAMPLE_INPUT.replace(
        "answer_unique: yes",
        "answer_unique: yes\nnum_tests:     12\nnum_solutions: 8\nnum_generators: 4")
    ci = parse_create_problem(with_counts)
    assert ci.num_tests == "12"
    assert ci.num_solutions == "8"
    assert ci.num_generators == "4"
    # omitted entirely -> None, not an error
    assert parse_create_problem(SAMPLE_INPUT).num_tests is None


def test_parse_rejects_non_integer_count():
    bad = SAMPLE_INPUT.replace("answer_unique: yes", "answer_unique: yes\nnum_tests:     many")
    try:
        parse_create_problem(bad)
    except InputError:
        pass
    else:
        raise AssertionError("non-integer num_tests should be rejected")


def test_access_reminder_empty_by_default_but_works_when_configured():
    from polygon_client.access import access_reminder
    assert access_reminder("owner", "prob") == ""  # no org grants configured
    msg = access_reminder("owner", "prob",
                          grants=[{"handle": "some_team", "permission": "WRITE"}])
    assert "some_team" in msg and "WRITE" in msg


def _make_orch(root: Path):
    ci = parse_create_problem(SAMPLE_INPUT)
    # sample_answers echoes back exactly what the human typed as expected
    # output, simulating Polygon's MA solution reproducing it correctly —
    # the happy path for verify_samples(). Tests that want a mismatch
    # override up.sample_answers after construction.
    up = RecordingUploader(owner="anshul_johri",
                           sample_answers={i: s.output for i, s in enumerate(ci.samples, start=1)})

    def runner(agent_name, payload):
        if agent_name == "spec-agent":
            (root / ci.name / "PROBLEM_SPEC.md").write_text("# PROBLEM_SPEC: eqpairs\n(ok)\n")
        else:
            _copy_fixture_artifacts(root / ci.name)
        return "ok"

    return Orchestrator(problems_root=root, runner=runner, uploader=up), ci, up


def test_gate_blocks_generation_before_approval():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        orch, ci, up = _make_orch(root)
        orch.start(ci)  # now AWAITING_APPROVAL
        try:
            orch.generate()  # must be blocked by the gate
        except GateError:
            pass
        else:
            raise AssertionError("generate() before approval must raise GateError")


def test_hand_forged_state_cannot_reach_live_upload():
    """Reproduces an observed real bypass: code with direct access to
    StateStore/Orchestrator hand-forges `state.json` (`store.state = X;
    store._write()`, skipping transition()) instead of calling
    orchestrator.approve(), then calls upload()/finalize() directly. This
    never goes through dispatch()/assert_can_dispatch() at all (generate() is
    never called), so the original gate never even runs — upload() and
    finalize() must independently refuse based on the audit trail."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        orch, ci, up = _make_orch(root)
        orch.start(ci)  # AWAITING_APPROVAL, with a real spec-agent dispatch on record

        # Forge straight into GENERATING_ARTIFACTS WITHOUT calling approve()
        # or transition() — exactly the pattern observed in practice.
        store = orch._store()
        store.state = State.GENERATING_ARTIFACTS
        store._write()
        _copy_fixture_artifacts(orch.problem_dir)  # pretend generation happened

        try:
            orch.upload()
        except PipelineHalt as e:
            assert "no genuine" in str(e)
        else:
            raise AssertionError("upload() proceeded on a hand-forged, never-approved state!")
        assert up.calls == [], "uploader must not have been touched"


def test_full_pipeline_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        orch, ci, up = _make_orch(root)

        spec_path = orch.start(ci)
        assert spec_path.exists()
        assert StateStore.load(orch.problem_dir).state == State.AWAITING_APPROVAL

        orch.approve()
        orch.generate()
        result = orch.run_after_approval()

        assert "Problem ready" in result
        assert "polygon.codeforces.com/p/anshul_johri/eqpairs" in result
        # no access_grants configured by default (config/org_defaults.yaml) ->
        # no manual-step reminder should appear in the final output
        assert "manual step" not in result.lower()

        # final state
        assert StateStore.load(orch.problem_dir).state == State.LINK_READY

        # upload drove the full tab sequence with commits, build_package was
        # triggered, and the sample-output verification read test_answer —
        # nothing here compiled or ran anything locally.
        names = up.call_names()
        for expected in ("create", "save_validator", "save_validator_test",
                         "set_checker", "save_script", "save_solution",
                         "set_limits", "save_tags", "build_package", "test_answer"):
            assert expected in names, f"uploader never called {expected}"
        assert names.count("commit") >= 6  # per-tab commits + final
        assert names.count("create") == 1, "create() must only ever run once"

        # ≥10 INVALID and ≥1 VALID validator tests reach the Validator tab (§8.3)
        vt_calls = [c for c in up.calls if c[0] == "save_validator_test"]
        invalid_vt = [c for c in vt_calls if c[1][2] == "INVALID"]
        valid_vt = [c for c in vt_calls if c[1][2] == "VALID"]
        assert len(invalid_vt) >= 10, f"only {len(invalid_vt)} INVALID validator tests uploaded"
        assert len(valid_vt) >= 3, f"only {len(valid_vt)} VALID validator tests uploaded"

        # meta.json's tags actually reached problem.saveTags (previously dead code)
        tags_call = next(c for c in up.calls if c[0] == "save_tags")
        assert set(tags_call[1][1]) == {"data structures", "combinatorics"}


def test_build_failure_routes_back_and_retry_is_idempotent():
    """A routable (non-escalating) Polygon build failure bounces back to
    GENERATING_ARTIFACTS; re-running upload() after the 'patch' must NOT
    re-create the problem (§11 idempotency) and a subsequent clean build
    completes normally."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        orch, ci, up = _make_orch(root)
        orch.start(ci)
        orch.approve()
        orch.generate()

        up.build_states = [("FAILED", "solution WA1.py violates tag(s): expected WA, got AC"),
                           ("READY", "")]

        created = orch.upload()
        try:
            orch.build_and_verify()
        except BuildFailure as e:
            assert e.result.state == "FAILED"
        else:
            raise AssertionError("expected BuildFailure on the first (routable) attempt")

        assert StateStore.load(orch.problem_dir).state == State.GENERATING_ARTIFACTS
        assert StateStore.load(orch.problem_dir).retry_count == 1

        create_calls_before = up.call_names().count("create")
        orch.upload()  # simulates re-running `finish` after the patch
        assert up.call_names().count("create") == create_calls_before, \
            "upload() re-created the problem on retry — not idempotent"

        orch.build_and_verify()  # now READY
        orch.verify_samples()
        result = orch.finalize(created)
        assert "Problem ready" in result


def test_build_failure_implicating_main_solution_escalates():
    """§1.5: a build failure that implicates the MA (or another reference)
    solution must escalate in code, never be treated as a routable patch."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        orch, ci, up = _make_orch(root)
        orch.start(ci)
        orch.approve()
        orch.generate()

        up.build_states = [("FAILED",
                           "solution correct.cpp violates tag(s): expected MA got WA")]

        orch.upload()
        try:
            orch.build_and_verify()
        except PipelineHalt as e:
            assert "correct.cpp" in str(e)
        else:
            raise AssertionError("expected an escalation, not a routable BuildFailure")
        assert StateStore.load(orch.problem_dir).state == State.ESCALATE_TO_HUMAN


def test_sample_mismatch_escalates():
    """verify_samples() halts if Polygon's MA-generated answer disagrees with
    the human's literal stated sample output — pure API-read + text diff, no
    local execution, but still never silently ignored (§1.5 spirit)."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        orch, ci, up = _make_orch(root)
        orch.start(ci)
        orch.approve()
        orch.generate()
        up.sample_answers = {1: "999\n"}  # deliberately wrong

        orch.upload()
        orch.build_and_verify()
        try:
            orch.verify_samples()
        except PipelineHalt as e:
            assert "sample" in str(e).lower()
        else:
            raise AssertionError("expected escalation on sample mismatch")
        assert StateStore.load(orch.problem_dir).state == State.ESCALATE_TO_HUMAN


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nAll {len(fns)} pipeline tests passed.")
