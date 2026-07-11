"""End-to-end test of local_harness against the eqpairs fixture (§10).

Compiles + runs real C++/Python, so it needs g++ and python3. Slower than the
gate tests. Run: python3 tests/test_harness.py

Also exercises the LocalHarnessInvocations backend, i.e. the confirmed answer to
the §9.4 invocations-API gap.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from local_harness.run import run_all
from polygon_client.invocations import LocalHarnessInvocations, VerdictMatrix

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "eqpairs"


def _require_toolchain():
    if not shutil.which("g++"):
        print("SKIP: g++ not available"); sys.exit(0)


def _mutated_fixture(mutate) -> Path:
    """Copy the eqpairs fixture into a fresh temp dir, apply `mutate(dir)`, and
    return the path. Caller owns cleanup (used within a single test's scope,
    so the OS temp dir is left for the process to clean up — these are small
    and short-lived)."""
    tmp = Path(tempfile.mkdtemp(prefix="eqpairs_mutated_"))
    dest = tmp / "eqpairs"
    shutil.copytree(FIXTURE, dest, ignore=shutil.ignore_patterns("_build", "tests"))
    mutate(dest)
    return dest


def test_harness_green_on_good_fixture():
    report = run_all(FIXTURE)
    assert report.ok, "eqpairs fixture should be fully GREEN:\n" + report.text()


def test_verdict_matrix_matches_expected_roster():
    report = run_all(FIXTURE)
    m = report.matrix
    # correct.* AC everywhere
    for sol in ("correct.cpp", "correct.py"):
        assert set(m[sol].values()) == {"AC"}, f"{sol} must be AC everywhere"
    # brute: AC on small/medium, TL on max only
    brute = m["brute.cpp"]
    assert "AC" in brute.values() and "TL" in brute.values()
    # every WA/RE solution non-AC somewhere
    for sol in ("WA1.py", "WA2.py", "WA3.cpp", "WA4.cpp"):
        assert set(m[sol].values()) != {"AC"}, f"{sol} must fail ≥1 test"
    # WA3 overflow bites ONLY at max scale (AC early, WA on the max test)
    assert "AC" in m["WA3.cpp"].values() and "WA" in m["WA3.cpp"].values()


def test_missing_expected_verdict_fails_harness():
    """A WA file with no EXPECTED_VERDICT tag must fail the local check —
    'non-AC somewhere, for any reason' is no longer sufficient (review
    finding #1: the harness previously couldn't tell a labeled bug from an
    unrelated crash)."""
    def strip_tag(d: Path):
        wa1 = d / "solutions" / "WA1.py"
        wa1.write_text(wa1.read_text().replace("# EXPECTED_VERDICT: WA\n", ""))
    d = _mutated_fixture(strip_tag)
    report = run_all(d)
    assert not report.ok
    assert "missing" in report.text() and "EXPECTED_VERDICT" in report.text()


def test_mismatched_expected_verdict_fails_harness():
    """A WA file that declares a verdict it never actually produces must fail
    — catches the exact 'crashes for an unrelated reason, label is
    decorative' failure mode the review flagged."""
    def wrong_tag(d: Path):
        wa1 = d / "solutions" / "WA1.py"
        wa1.write_text(wa1.read_text().replace(
            "# EXPECTED_VERDICT: WA", "# EXPECTED_VERDICT: RE"))
    d = _mutated_fixture(wrong_tag)
    report = run_all(d)
    assert not report.ok
    assert "declared EXPECTED_VERDICT=RE but never actually produced it" in report.text()


def test_spec_consistency_catches_statement_validator_drift():
    """Statement/validator bound drift (review finding #3) is one of the most
    common real CF/ICPC bugs — verify the heuristic check actually catches a
    deliberately introduced mismatch, not just that it stays quiet on the
    already-consistent fixture."""
    def drift(d: Path):
        v = d / "validator.cpp"
        # spec says n <= 100000; make the validator allow double that.
        v.write_text(v.read_text().replace(
            'inf.readInt(1, 100000, "n")', 'inf.readInt(1, 200000, "n")'))
    d = _mutated_fixture(drift)
    report = run_all(d)
    assert not report.ok
    assert "drift" in report.text() and "'n'" in report.text()


def test_invocations_backend_returns_matrix():
    backend = LocalHarnessInvocations(problem_dir=FIXTURE)
    run_id = backend.run(problem_id=999)
    vm = backend.results(problem_id=999, run_id=run_id)
    assert isinstance(vm, VerdictMatrix)
    assert vm.verdicts_for("correct.cpp")  # non-empty
    assert set(vm.verdicts_for("correct.cpp").values()) == {"AC"}


if __name__ == "__main__":
    _require_toolchain()
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nAll {len(fns)} harness tests passed.")
