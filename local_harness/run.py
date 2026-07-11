"""Full local self-check (§10). Only a fully green run lets the orchestrator
leave LOCAL_SELF_CHECK.

Sequence: compile_all → materialize → validator_stress → cross_check → tle_probe
→ judge (verdict matrix) → roster-behavior assertions. Tests are materialized
once and shared across the checks.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from .problem import Problem
from .compile import compile_all
from .materialize import materialize
from .validator_stress import validator_stress
from .cross_check import cross_check
from .tle_probe import tle_probe
from .judge import judge


@dataclass
class HarnessReport:
    ok: bool
    sections: list[str] = field(default_factory=list)
    matrix: dict[str, dict[int, str]] = field(default_factory=dict)

    def text(self) -> str:
        head = "LOCAL SELF-CHECK: " + ("✅ GREEN" if self.ok else "❌ RED")
        return head + "\n\n" + "\n\n".join(self.sections)


def _check_roster(problem_dir: Path, matrix: dict[str, dict[int, str]]) -> tuple[bool, str]:
    """Assert the expected verdict pattern (§15): correct.* AC everywhere;
    every WA*/RE* solution non-AC somewhere."""
    p = Problem.load(problem_dir)
    ok = True
    lines = []
    for sol, row in matrix.items():
        verdicts = set(row.values())
        stem = sol.lower()
        if stem.startswith("correct"):
            if verdicts != {"AC"}:
                ok = False
                bad = {i: v for i, v in row.items() if v != "AC"}
                lines.append(f"  ❌ {sol} must be AC everywhere; got {bad}")
            else:
                lines.append(f"  ✅ {sol}: AC on all")
        elif stem.startswith("brute"):
            lines.append(f"  •  {sol}: {sorted(verdicts)} (timing checked by tle_probe)")
        elif stem.startswith("wa") or stem.startswith("re"):
            if verdicts == {"AC"}:
                ok = False
                lines.append(f"  ❌ {sol} is AC on ALL tests — broken fixture (§15)")
            else:
                lines.append(f"  ✅ {sol}: non-AC on ≥1 ({sorted(verdicts)})")
    header = "roster behavior: PASS" if ok else "roster behavior: FAIL"
    return ok, header + "\n" + "\n".join(lines)


def run_all(problem_dir: Path) -> HarnessReport:
    rep = HarnessReport(ok=True)

    def add(ok: bool, text: str):
        rep.sections.append(text)
        if not ok:
            rep.ok = False

    c_ok, c_txt = compile_all(problem_dir)
    add(c_ok, c_txt)
    if not c_ok:
        return rep  # nothing else can run

    m_ok, tests, m_txt = materialize(problem_dir)
    add(m_ok, m_txt)
    if not m_ok:
        return rep

    add(*validator_stress(problem_dir, tests))
    add(*cross_check(problem_dir, tests))
    add(*tle_probe(problem_dir, tests))

    jr = judge(problem_dir, tests)
    add(jr.ok, jr.report)
    rep.matrix = jr.matrix
    if jr.ok:
        add(*_check_roster(problem_dir, jr.matrix))

    return rep


if __name__ == "__main__":
    report = run_all(Path(sys.argv[1]))
    print(report.text())
    sys.exit(0 if report.ok else 1)
