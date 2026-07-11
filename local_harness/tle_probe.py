"""Brute TLE-distribution probe (§10, §12).

Runs brute.cpp against every test with a wall-clock cap of 3× time_limit (a fast
local proxy for the real judge). The required pattern: brute passes on
small/medium tiers and EXCEEDS the cap on the max tier only.

Failure modes flagged back to generator-agent:
  * brute passes everything  → test plan too weak (need bigger/adversarial max)
  * brute exceeds everywhere → small/medium tiers too big (loosen them)
"""

from __future__ import annotations

from pathlib import Path

from ._exec import compile_cpp, run, warmup
from .problem import Problem
from .materialize import materialize, MaterializedTest

CAP_MULTIPLIER = 3


def tle_probe(problem_dir: Path,
              tests: list[MaterializedTest] | None = None) -> tuple[bool, str]:
    p = Problem.load(problem_dir)
    brute = p.solutions_dir / "brute.cpp"
    if not brute.exists():
        return True, "tle_probe: SKIP (no brute.cpp)"

    res = compile_cpp(brute, p.build_dir / "brute", warnings_as_errors=False)
    if not res.ok:
        return False, f"tle_probe: FAIL (brute won't compile)\n{res.stderr[:300]}"
    bbin = p.build_dir / "brute"
    warmup([str(bbin)])

    if tests is None:
        ok, tests, mlog = materialize(problem_dir)
        if not ok:
            return False, mlog

    cap = p.time_limit_ms * CAP_MULTIPLIER
    passed, exceeded = [], []
    lines: list[str] = []
    for t in tests:
        r = run([str(bbin)], stdin_path=t.path, timeout_ms=cap)
        if r.timed_out:
            exceeded.append(t.index)
            lines.append(f"  test {t.index:>3}: >CAP ({cap}ms)   [{t.source}]")
        else:
            passed.append(t.index)
            lines.append(f"  test {t.index:>3}: {r.wall_ms:7.1f}ms   [{t.source}]")

    ok = bool(passed) and bool(exceeded)
    if not exceeded:
        verdict = ("tle_probe: FAIL — brute passes EVERYTHING; test plan too weak. "
                   "Regenerate the max tier with larger n / adversarial pattern (§12).")
    elif not passed:
        verdict = ("tle_probe: FAIL — brute exceeds EVERYWHERE; small/medium tiers "
                   "too big. Loosen those tier sizes (§12).")
    else:
        verdict = (f"tle_probe: PASS — brute AC on {len(passed)} tier(s), "
                   f"TL on {len(exceeded)} (partial pattern as required).")
    return ok, verdict + "\n" + "\n".join(lines)
