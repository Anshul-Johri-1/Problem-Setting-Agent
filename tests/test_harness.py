"""End-to-end test of local_harness against the eqpairs fixture (§10).

Compiles + runs real C++/Python, so it needs g++ and python3. Slower than the
gate tests. Run: python3 tests/test_harness.py

Also exercises the LocalHarnessInvocations backend, i.e. the confirmed answer to
the §9.4 invocations-API gap.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from local_harness.run import run_all
from polygon_client.invocations import LocalHarnessInvocations, VerdictMatrix

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "eqpairs"


def _require_toolchain():
    if not shutil.which("g++"):
        print("SKIP: g++ not available"); sys.exit(0)


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
