"""Validator stress (§10, §8.3).

Every real generated test must PASS the validator (exit 0). Every malformed
input in validator_stress/ must be REJECTED (non-zero exit). Requires
>= min_validator_stress_tests (org_defaults) malformed cases.

Also checks validator_valid/ (the genuinely-valid corpus uploaded to Polygon's
Validator tab as VALID tests, §8.3): each file must PASS both as-is AND with
its trailing newline(s) stripped. The trimmed check simulates exactly what
Polygon's `problem.saveValidatorTest` does to manually-uploaded test input —
catching, locally, the class of bug where a validator's bare `inf.readEoln()`
(strict-mode, no EOF fallback) on the FILE'S LAST LINE spuriously rejects a
valid test the moment it's uploaded that way. See tutorials/validator.md for
the fix (guard only that last `readEoln()` with
`if (!inf.eof()) inf.readEoln();` — never intermediate ones, and never
`seekEof()`, which would also swallow a stray trailing space).
"""

from __future__ import annotations

from pathlib import Path

from ._exec import compile_cpp, run
from .problem import Problem
from .materialize import materialize, MaterializedTest

MIN_STRESS = 10  # org_defaults.min_validator_stress_tests
MIN_VALID = 3    # minimum genuinely-valid corpus size


def _rstrip_newlines(text: str) -> str:
    return text.rstrip("\r\n")


def validator_stress(problem_dir: Path,
                     tests: list[MaterializedTest] | None = None) -> tuple[bool, str]:
    p = Problem.load(problem_dir)
    validator_src = p.dir / "validator.cpp"
    if not validator_src.exists():
        return False, "validator_stress: FAIL (no validator.cpp)"

    res = compile_cpp(validator_src, p.build_dir / "validator")
    if not res.ok:
        return False, f"validator_stress: FAIL (validator won't compile)\n{res.stderr[:300]}"
    vbin = p.build_dir / "validator"

    if tests is None:
        ok, tests, mlog = materialize(problem_dir)
        if not ok:
            return False, mlog

    lines: list[str] = []
    ok = True

    # valid tests (the real generated/sample test set) must pass
    for t in tests:
        r = run([str(vbin)], stdin_path=t.path)
        if r.exit_code != 0:
            ok = False
            lines.append(f"  ❌ valid test {t.index} REJECTED: {r.stderr.strip()[:120]}")
    lines.append(f"  {len([t for t in tests])} valid tests checked")

    # genuinely-valid corpus (validator_valid/) must pass raw AND trimmed
    valid_files = sorted(p.valid_dir.glob("*.txt")) if p.valid_dir.exists() else []
    nonempty_valid = [vf for vf in valid_files if vf.read_text() != ""]
    if nonempty_valid and len(nonempty_valid) < MIN_VALID:
        ok = False
        lines.append(f"  ❌ only {len(nonempty_valid)} validator_valid/ inputs "
                     f"(need ≥ {MIN_VALID} if any are provided)")
    for vf in nonempty_valid:
        raw = vf.read_text()
        r_raw = run([str(vbin)], stdin_path=vf)
        if r_raw.exit_code != 0:
            ok = False
            lines.append(f"  ❌ validator_valid/{vf.name} REJECTED as-is: "
                         f"{r_raw.stderr.strip()[:120]}")
            continue
        trimmed_path = p.build_dir / f"_vt_trim_{vf.stem}.txt"
        trimmed_path.write_text(_rstrip_newlines(raw))
        r_trim = run([str(vbin)], stdin_path=trimmed_path)
        if r_trim.exit_code != 0:
            ok = False
            lines.append(
                f"  ❌ validator_valid/{vf.name} REJECTED once trailing newline is "
                f"stripped (Polygon will trim it on upload) — validator needs "
                f"`if (!inf.eof()) inf.readEoln();` on its LAST line only "
                f"instead of a bare `inf.readEoln();` there (see "
                f"tutorials/validator.md)")
    if nonempty_valid:
        lines.append(f"  {len(nonempty_valid)} validator_valid/ inputs checked "
                     f"(raw + trimmed)")

    # malformed inputs must be rejected
    malformed = sorted(p.stress_dir.glob("*.txt")) if p.stress_dir.exists() else []
    nonempty_malformed = [mf for mf in malformed if mf.read_text() != ""]
    if len(nonempty_malformed) < MIN_STRESS:
        ok = False
        lines.append(f"  ❌ only {len(nonempty_malformed)} malformed inputs (need ≥ {MIN_STRESS})")
    for mf in malformed:
        r = run([str(vbin)], stdin_path=mf)
        if r.exit_code == 0:
            ok = False
            lines.append(f"  ❌ malformed '{mf.name}' was ACCEPTED (should be rejected)")
    lines.append(f"  {len(malformed)} malformed inputs checked")

    header = "validator_stress: PASS" if ok else "validator_stress: FAIL"
    return ok, header + "\n" + "\n".join(lines)
