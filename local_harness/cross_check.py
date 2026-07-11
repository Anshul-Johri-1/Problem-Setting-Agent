"""Diff correct.cpp vs correct.py across every test (§10).

Any output mismatch HALTS and surfaces to the human as a likely spec ambiguity —
not an auto-fixable bug (§1.5). Comparison is token-normalized (whitespace-
insensitive) since exact formatting is the checker's job, not this cross-check's.
"""

from __future__ import annotations

from pathlib import Path

from ._exec import run, warmup
from .problem import Problem
from .judge import _runnable
from .materialize import materialize, MaterializedTest


def _norm(text: str) -> list[str]:
    return text.split()


def cross_check(problem_dir: Path,
                tests: list[MaterializedTest] | None = None) -> tuple[bool, str]:
    p = Problem.load(problem_dir)
    py = p.solutions_dir / "correct.py"
    cpp = p.solutions_dir / "correct.cpp"
    if not (py.exists() and cpp.exists()):
        return True, "cross_check: SKIP (need both correct.py and correct.cpp)"

    if tests is None:
        ok, tests, mlog = materialize(problem_dir)
        if not ok:
            return False, mlog

    py_cmd = _runnable(py, p.build_dir)
    cpp_cmd = _runnable(cpp, p.build_dir)
    warmup(py_cmd); warmup(cpp_cmd)

    mismatches: list[str] = []
    for t in tests:
        r_py = run(py_cmd, stdin_path=t.path, timeout_ms=max(p.time_limit_ms * 5, 5000))
        r_cpp = run(cpp_cmd, stdin_path=t.path, timeout_ms=max(p.time_limit_ms * 5, 5000))
        if r_py.exit_code != 0 or r_cpp.exit_code != 0:
            mismatches.append(f"  test {t.index}: a reference solution crashed")
            continue
        if _norm(r_py.stdout) != _norm(r_cpp.stdout):
            mismatches.append(f"  test {t.index}: correct.py vs correct.cpp DIFFER ({t.source})")

    if mismatches:
        return False, ("cross_check: FAIL — reference solutions disagree (likely "
                       "spec ambiguity; HALT & escalate)\n" + "\n".join(mismatches))
    return True, f"cross_check: PASS ({len(tests)} tests agree)"
