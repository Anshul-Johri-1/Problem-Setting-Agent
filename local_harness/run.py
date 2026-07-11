"""Full local self-check (§10). Only a fully green run lets the orchestrator
leave LOCAL_SELF_CHECK.

Sequence: compile_all → materialize → validator_stress → cross_check →
tle_probe → sanitize_check → judge (verdict matrix) → roster-behavior
assertions → spec/validator constraint consistency. Tests are materialized
once and shared across the checks.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .problem import Problem
from .compile import compile_all
from .materialize import materialize
from .validator_stress import validator_stress
from .cross_check import cross_check
from .tle_probe import tle_probe
from .sanitize_check import sanitize_check
from .judge import judge
from .spec_consistency import spec_consistency
from .stress import stress_correctness, tle_search

# A WA/RE/TL/ML file MUST declare which verdict it expects, e.g.:
#   // EXPECTED_VERDICT: WA          (C++)
#   # EXPECTED_VERDICT: RE           (Python)
# Checked in the first 15 lines. This exists specifically so "non-AC
# somewhere" can't silently mean "crashed for an unrelated reason and never
# actually exercised the claimed bug" — see docs/review notes.
_EXPECTED_VERDICT_RE = re.compile(r"EXPECTED_VERDICT:\s*(AC|WA|RE|TL|ML|RJ)")
_VALID_VERDICTS = {"AC", "WA", "RE", "TL", "ML", "RJ"}


@dataclass
class HarnessReport:
    ok: bool
    sections: list[str] = field(default_factory=list)
    matrix: dict[str, dict[int, str]] = field(default_factory=dict)

    def text(self) -> str:
        head = "LOCAL SELF-CHECK: " + ("✅ GREEN" if self.ok else "❌ RED")
        return head + "\n\n" + "\n\n".join(self.sections)


def _declared_expected_verdict(sol_path: Path) -> str | None:
    head = "\n".join(sol_path.read_text().splitlines()[:15])
    m = _EXPECTED_VERDICT_RE.search(head)
    return m.group(1) if m else None


def _check_roster(problem_dir: Path, matrix: dict[str, dict[int, str]]) -> tuple[bool, str]:
    """Assert the expected verdict pattern (§15): correct.* AC everywhere;
    every WA*/RE* solution non-AC somewhere AND matching its declared
    EXPECTED_VERDICT tag — not just "some non-AC verdict, any reason"."""
    p = Problem.load(problem_dir)
    ok = True
    lines = []
    for sol, row in matrix.items():
        verdicts = set(row.values())
        stem = sol.lower()
        sol_path = p.solutions_dir / sol

        if stem.startswith("correct"):
            if verdicts != {"AC"}:
                ok = False
                bad = {i: v for i, v in row.items() if v != "AC"}
                lines.append(f"  ❌ {sol} must be AC everywhere; got {bad}")
            else:
                lines.append(f"  ✅ {sol}: AC on all")

        elif stem.startswith("brute"):
            lines.append(f"  •  {sol}: {sorted(verdicts)} (timing checked by tle_probe)")

        elif stem.startswith("tle"):
            # Near-miss too-slow target: must be AC on small (it's a correct
            # algorithm, not a brute) AND declare + produce TL. tle_search
            # separately proves the adversarial tier actually forces it over.
            expected = _declared_expected_verdict(sol_path)
            if expected != "TL":
                ok = False
                lines.append(
                    f"  ❌ {sol}: a too-slow target must declare `EXPECTED_VERDICT: TL` "
                    f"(got {expected!r}) — it models a near-correct-but-slow submission")
            elif "TL" not in verdicts:
                ok = False
                lines.append(
                    f"  ❌ {sol}: declared too-slow but never TLE'd on the fixed set "
                    f"({sorted(verdicts)}) — the adversarial tier doesn't force it over "
                    f"(see tle_search / generator-agent)")
            elif "AC" not in verdicts:
                lines.append(
                    f"  ⚠️  {sol}: TL on all tests, never AC — this is a brute, not a "
                    f"near-miss; give it a small tier it passes so it models a real "
                    f"competitor's submission")
            else:
                lines.append(f"  ✅ {sol}: AC on small + TL on max (near-miss target)")

        elif stem.startswith("wa") or stem.startswith("re"):
            if verdicts == {"AC"}:
                ok = False
                lines.append(f"  ❌ {sol} is AC on ALL tests — broken fixture (§15)")
                continue
            expected = _declared_expected_verdict(sol_path)
            if expected is None:
                ok = False
                lines.append(
                    f"  ❌ {sol}: missing `EXPECTED_VERDICT: <verdict>` header — "
                    f"declare which verdict this bug is supposed to produce "
                    f"(WA/RE/TL/ML/RJ), don't just rely on 'non-AC somewhere'")
            elif expected not in verdicts:
                ok = False
                lines.append(
                    f"  ❌ {sol}: declared EXPECTED_VERDICT={expected} but never "
                    f"actually produced it (got {sorted(verdicts)}) — the claimed "
                    f"bug may not be the real reason this fails; verify the header "
                    f"matches what actually happens")
            else:
                lines.append(f"  ✅ {sol}: non-AC on ≥1, matches declared "
                             f"EXPECTED_VERDICT={expected} ({sorted(verdicts)})")

    header = "roster behavior: PASS" if ok else "roster behavior: FAIL"
    return ok, header + "\n" + "\n".join(lines) + "\n" + _overlap_report(matrix)


def _overlap_report(matrix: dict[str, dict[int, str]]) -> str:
    """Soft, non-blocking signal (§0 file-count quotas are a proxy metric):
    flag WA/RE files whose failing-test SET is nearly identical to another's —
    a sign the roster grew to hit a quota rather than to add real coverage."""
    fail_sets: dict[str, frozenset[int]] = {}
    for sol, row in matrix.items():
        stem = sol.lower()
        if stem.startswith("wa") or stem.startswith("re"):
            failing = frozenset(i for i, v in row.items() if v != "AC")
            if failing:
                fail_sets[sol] = failing

    warnings = []
    names = sorted(fail_sets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sa, sb = fail_sets[a], fail_sets[b]
            union = sa | sb
            if not union:
                continue
            jaccard = len(sa & sb) / len(union)
            if jaccard >= 0.8 and len(union) >= 2:
                warnings.append(
                    f"  ⚠️  {a} and {b} fail on nearly the same tests "
                    f"({jaccard*100:.0f}% overlap) — consider whether they're "
                    f"actually testing distinct bugs, or should be consolidated")
    if not warnings:
        return "coverage overlap: no significant redundancy detected"
    return "coverage overlap:\n" + "\n".join(warnings)


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
    add(*sanitize_check(problem_dir, tests))
    add(*spec_consistency(problem_dir))

    jr = judge(problem_dir, tests)
    add(jr.ok, jr.report)
    rep.matrix = jr.matrix
    if jr.ok:
        add(*_check_roster(problem_dir, jr.matrix))
        # Stress phase (§10.5): search for the tests the fixed script missed.
        # Correctness search uses the just-computed matrix (only searches WAs
        # the fixed set failed to catch); TLE search sweeps adversarial seeds
        # against the declared too-slow targets. Both SKIP cleanly when N/A.
        add(*stress_correctness(problem_dir, tests, jr.matrix))
    add(*tle_search(problem_dir))

    return rep


if __name__ == "__main__":
    report = run_all(Path(sys.argv[1]))
    print(report.text())
    sys.exit(0 if report.ok else 1)
