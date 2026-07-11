"""Sanitizer pass for trusted solutions (§10 addendum).

-O2 (the build used everywhere else in the harness) can hide undefined
behavior — signed overflow that "happens to work" under one optimizer's
instruction selection, an out-of-bounds read that doesn't crash locally but
does under Polygon's actual compiler/judge box, an uninitialized read that
reads zero here and garbage there. "It passed locally" is not evidence a
solution is UB-free; it's evidence the UB didn't bite on THIS run, on THIS
machine. This compiles every solution the harness treats as ground truth (the
MA solution, plus any other file tagged effectively-correct — i.e. C++ files
whose name starts with "correct") under ASan+UBSan and runs them against
every materialized test, independently of the main -O2 judging pass.

Deliberately NOT applied to brute/WA/RE files — they're expected to misbehave;
running them under UBSan would just produce expected noise.
"""

from __future__ import annotations

from pathlib import Path

from ._exec import compile_cpp, run, warmup
from .problem import Problem
from .materialize import materialize, MaterializedTest

_SANITIZER_MARKERS = ("ERROR: AddressSanitizer", "runtime error:", "SUMMARY: ")


def _trusted_cpp_solutions(p: Problem) -> list[Path]:
    out = []
    for sol in p.solution_files():
        if sol.suffix != ".cpp":
            continue
        if sol.name == p.main_solution or sol.stem.lower().startswith("correct"):
            out.append(sol)
    return out


def sanitize_check(problem_dir: Path,
                   tests: list[MaterializedTest] | None = None) -> tuple[bool, str]:
    p = Problem.load(problem_dir)
    targets = _trusted_cpp_solutions(p)
    if not targets:
        return True, "sanitize_check: SKIP (no C++ trusted solution to check)"

    if tests is None:
        ok, tests, mlog = materialize(problem_dir)
        if not ok:
            return False, mlog

    lines: list[str] = []
    overall_ok = True
    for sol in targets:
        sbin = p.build_dir / f"{sol.stem}_asan"
        res = compile_cpp(sol, sbin, warnings_as_errors=False, sanitize=True)
        if not res.ok:
            overall_ok = False
            lines.append(f"  ❌ {sol.name}: sanitized build failed to compile\n"
                         f"      {res.stderr.strip()[:300]}")
            continue

        cmd = [str(sbin)]
        warmup(cmd)
        # Sanitized binaries are much slower than -O2; give generous headroom
        # so this checks correctness, not performance.
        timeout_ms = max(p.time_limit_ms * 8, 8000)
        failed_on: list[str] = []
        for t in tests:
            r = run(cmd, stdin_path=t.path, timeout_ms=timeout_ms)
            if r.timed_out:
                continue  # sanitized slowdown, not a correctness signal here
            hit = r.exit_code != 0 or any(m in r.stderr for m in _SANITIZER_MARKERS)
            if hit:
                overall_ok = False
                snippet = r.stderr.strip().splitlines()
                snippet = "\n".join(snippet[:6])
                failed_on.append(f"    test {t.index} ({t.source}):\n"
                                 f"      {snippet}")
        if failed_on:
            lines.append(f"  ❌ {sol.name}: sanitizer detected an issue\n" + "\n".join(failed_on))
        else:
            lines.append(f"  ✅ {sol.name}: clean under ASan+UBSan on {len(tests)} tests")

    header = "sanitize_check: PASS" if overall_ok else "sanitize_check: FAIL"
    return overall_ok, header + "\n" + "\n".join(lines)
