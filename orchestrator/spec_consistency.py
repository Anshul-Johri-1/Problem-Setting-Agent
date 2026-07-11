"""Statement/validator numeric-bounds consistency check (§10 addendum).

Pure text/regex parsing of two already-written files — no compilation, no
execution of any solution/generator/validator. This is the one static check
kept locally; every other correctness check now runs on Polygon itself (see
orchestrator/pipeline.py::build_and_verify).

Heuristic, best-effort sanity check: extracts (variable, lo, hi) triples from
validator.cpp's inf.readInt/readLong calls, and separately from the
Constraints table in the approved PROBLEM_SPEC.md, then flags any pair it can
CONFIDENTLY parse on both sides that disagrees. This is one of the single most
common real-world CF/ICPC bugs — the statement says one bound, the validator
enforces another, because they're written by two different agents from the
same spec and nothing diffs them.

Deliberately conservative: only compares rows it can parse with high
confidence (a clean two-sided numeric range, a validator call whose declared
name matches a spec variable). Ambiguous rows are skipped, not force-matched —
a check that produces false positives gets disabled by the team, which is
worse than a check that occasionally misses a row it can't confidently parse.
"""

from __future__ import annotations

import re
from pathlib import Path

_READ_CALL_RE = re.compile(
    r'inf\.read(?:Int|Long)\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*"([^"]+)"\s*\)'
)

_TWO_SIDED_RE = re.compile(
    r'([-\d][^<>=]*?)\s*(?:\\le|\\leq|<=|≤|<)\s*(\S+)\s*(?:\\le|\\leq|<=|≤|<)\s*([-\d][^<>=]*?)$'
)


def _normalize(text: str) -> str:
    text = text.replace("$", "").replace("\\,", "").replace("{", "").replace("}", "")
    text = text.replace("\\cdot", "*").replace("\\times", "*")
    text = text.replace("×", "*").replace("·", "*")
    text = text.replace("\\le", "<=").replace("\\leq", "<=")
    return text.strip()


def _eval_num(text: str) -> float | None:
    """Parse a normalized numeric literal: 10^9, 2*10^5, -10^9, 200000, ..."""
    text = text.strip()
    neg = text.startswith("-")
    if neg:
        text = text[1:].strip()
    m = re.match(r'^(\d+(?:\.\d+)?)(?:\s*\*\s*10\s*\^\s*(\d+))?(?:\s*\^\s*(\d+))?$', text)
    if not m:
        return None
    base = float(m.group(1))
    if m.group(2):
        val = base * (10 ** int(m.group(2)))
    elif m.group(3):
        val = base ** int(m.group(3))
    else:
        val = base
    return -val if neg else val


def _validator_bounds(validator_src: str) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for lo, hi, name in _READ_CALL_RE.findall(validator_src):
        out[name] = (float(lo), float(hi))
    return out


def _spec_bounds(spec_md: str) -> dict[str, tuple[float, float]]:
    m = re.search(r'##\s*Constraints\s*\n(.*?)(?=\n##\s|\Z)', spec_md, re.DOTALL)
    if not m:
        return {}
    out: dict[str, tuple[float, float]] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        var_raw, range_raw = cells[0], cells[1]
        var = _normalize(var_raw).replace("\\", "").strip()
        if not var or var.lower() in ("variable", "---") or set(var) <= {"-"}:
            continue
        range_text = _normalize(range_raw)
        rm = _TWO_SIDED_RE.search(range_text)
        if not rm:
            continue
        lo, hi = _eval_num(rm.group(1)), _eval_num(rm.group(3))
        if lo is None or hi is None:
            continue
        out[var] = (lo, hi)
    return out


def _base_name(name: str) -> str:
    """'a_i' -> 'a', 'a_1' -> 'a' — collapse array-element subscripts so a
    per-element validator bound can match a spec row describing the array."""
    return re.split(r"[_,\s]", name, 1)[0]


def spec_consistency(problem_dir: Path) -> tuple[bool, str]:
    spec_path = problem_dir / "PROBLEM_SPEC.md"
    validator_path = problem_dir / "validator.cpp"
    if not spec_path.exists() or not validator_path.exists():
        return True, "spec_consistency: SKIP (no PROBLEM_SPEC.md and/or validator.cpp)"

    v_bounds = _validator_bounds(validator_path.read_text())
    s_bounds = _spec_bounds(spec_path.read_text())
    if not v_bounds or not s_bounds:
        return True, "spec_consistency: SKIP (nothing confidently parseable on one side)"

    lines: list[str] = []
    ok = True
    checked = 0
    for vname, (vlo, vhi) in sorted(v_bounds.items()):
        base = _base_name(vname)
        candidates = [k for k in s_bounds if _base_name(k) == base or k == vname]
        if not candidates:
            continue
        sname = candidates[0]
        slo, shi = s_bounds[sname]
        checked += 1
        if (vlo, vhi) != (slo, shi):
            ok = False
            lines.append(
                f"  ❌ '{vname}': validator enforces [{vlo:g}, {vhi:g}] but "
                f"PROBLEM_SPEC.md's Constraints table states [{slo:g}, {shi:g}] "
                f"for '{sname}' — statement/validator drift")
        else:
            lines.append(f"  ✅ '{vname}': validator and spec agree on [{vlo:g}, {vhi:g}]")

    if checked == 0:
        return True, "spec_consistency: SKIP (no confidently-matchable variable names)"
    header = "spec_consistency: PASS" if ok else "spec_consistency: FAIL"
    return ok, header + "\n" + "\n".join(lines)
