"""Stress phase (§10.5) — hunt for the tests the fixed script missed.

The rest of the harness verifies a *fixed*, human-approved test set: it runs
every solution against `script.txt`'s tests and checks the verdict matrix. That
only ever confirms what the setter already thought to test. This module instead
*searches* for a counterexample the fixed set doesn't contain — the standard
professional defense, and the only mechanism that meets the bar "if someone
submits Dijkstra without `if d > dist[u]: continue`, a test must give TLE."

Two independent searches, both bounded (they run inside the local-check gate):

1. `stress_correctness` — small-random differential search against the WA files.
   A WA that slips through every fixed test is either (a) genuinely wrong but
   under-tested — in which case this finds the concrete small input that kills
   it, to be adopted as a real test — or (b) not actually wrong, a fixture bug.
   It distinguishes the two and routes accordingly, instead of leaving "WA is
   AC everywhere" as an unexplained failure.

2. `tle_search` — worst-case sweep against the declared too-slow targets
   (`solutions/tle*`, `meta.too_slow_targets`). For each target it re-runs the
   adversarial generator's patterns over several seeds at max scale, keeping the
   worst runtime. It asserts (i) the intended solution stays comfortably under
   the limit on all of them and (ii) each too-slow target is forced OVER the
   limit by at least one. If the hardcoded script seed was weak (a line graph
   that never triggers the stale-check blow-up), the sweep finds a seed that
   does — or proves the current patterns can't, which is a generator-agent
   patch, not a silent pass.

Neither search invents new *shapes* — that's generator-agent's job, guided by
`tutorials/generator.md`. They find weak seeds/params of the shapes that exist
and prove whether the declared traps are actually enforced.
"""

from __future__ import annotations

import shlex
import time
from pathlib import Path

from ._exec import run, warmup
from .problem import Problem
from .judge import _runnable, _checker_binary
from .materialize import materialize, MaterializedTest

# Tunable via meta.json "stress": {...}; these are the org defaults.
STRESS_DEFAULTS = {
    # correctness search
    "corr_iters": 300,           # max random probes per AC-everywhere WA
    "corr_budget_ms": 4000,      # wall-clock cap for the whole correctness search
    # tle search
    "tle_seeds": 4,              # extra reseeds per adversarial pattern to sweep
    "tle_configs_cap": 8,        # hard cap on total generator invocations swept
    # A too-slow target must exceed the REAL time limit locally by at least this
    # factor on its worst swept config. >1.0 (not a token 1.01) because local
    # timing can't resolve a near-miss reliably — see tutorials/generator.md's
    # margin discipline: build the anti-test so the bad solution is many× over,
    # never barely over, precisely so this check survives judge-hardware drift.
    "tle_target_min_ratio": 1.0,
    # The intended solution must stay UNDER this fraction of the limit on every
    # swept adversarial config (headroom for slower judge hardware).
    "correct_max_ratio": 0.7,
}


def _script_lines(p: Problem) -> list[str]:
    script = p.dir / "script.txt"
    if not script.exists():
        return []
    out = []
    for raw in script.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def _lines_for(p: Problem, needle: str) -> list[str]:
    """Script lines whose generator (first token) name contains `needle`."""
    return [ln for ln in _script_lines(p)
            if needle in shlex.split(ln)[0].lower()]


def _gen_bin(p: Problem, line: str) -> Path:
    return p.build_dir / Path(shlex.split(line)[0]).stem


def _run_generator(p: Problem, line: str, reseed: int | None) -> str | None:
    """Run a script generator line, optionally appending a reseeding token
    (testlib seeds its RNG from the whole argv, so an extra distinct token
    yields a different case of the SAME pattern). Returns stdin text or None."""
    parts = shlex.split(line)
    args = parts[1:] + ([str(reseed)] if reseed is not None else [])
    gen_bin = _gen_bin(p, line)
    if not gen_bin.exists():
        return None
    res = run([str(gen_bin), *args], timeout_ms=15000)
    return res.stdout if res.exit_code == 0 else None


# --------------------------------------------------------------------------- #
def stress_correctness(problem_dir: Path,
                       tests: list[MaterializedTest] | None = None,
                       matrix: dict[str, dict[int, str]] | None = None) -> tuple[bool, str]:
    """Differential random search for WA files the fixed test set fails to
    distinguish from the correct solution. Only WAs that are AC on EVERY fixed
    test are searched (the ones the fixed set missed); WAs already failing are
    reported as distinguished and left alone, so a well-built problem pays
    almost nothing here."""
    p = Problem.load(problem_dir)
    wa = p.wa_files()
    if not wa:
        return True, "stress_correctness: SKIP (no WA files)"

    rand_lines = _lines_for(p, "random")
    if matrix is None:
        return True, "stress_correctness: SKIP (no verdict matrix supplied)"

    # Which WAs slipped through every fixed test?
    slipped = []
    distinguished = []
    for f in wa:
        row = matrix.get(f.name, {})
        if row and set(row.values()) == {"AC"}:
            slipped.append(f)
        else:
            distinguished.append(f.name)

    lines = []
    if distinguished:
        lines.append(f"  ✓ distinguished by the fixed test set: {', '.join(distinguished)}")
    if not slipped:
        return True, "stress_correctness: PASS (every WA already fails a fixed test)\n" + \
            "\n".join(lines)

    if not rand_lines:
        # We can't search, but these WAs are already roster-failures; be explicit.
        lines.append("  ⚠️  cannot random-search (no generator_random* line in "
                     "script.txt) — the WA(s) below are AC on every fixed test "
                     "and can't be auto-diagnosed")
        lines.append("  ❌ AC-on-all WA(s): " + ", ".join(f.name for f in slipped))
        return False, "stress_correctness: FAIL\n" + "\n".join(lines)

    base_line = rand_lines[0]
    checker = _checker_binary(p)
    main_cmd = _runnable(p.solutions_dir / p.main_solution, p.build_dir)
    warmup(main_cmd)
    wa_cmds = {f.name: _runnable(f, p.build_dir) for f in slipped}
    for c in wa_cmds.values():
        warmup(c)

    found_dir = p.build_dir / "stress_found"
    found_dir.mkdir(exist_ok=True)

    iters = int(p.stress_cfg("corr_iters"))
    budget_ms = int(p.stress_cfg("corr_budget_ms"))
    tl = max(p.time_limit_ms * 5, 5000)

    unresolved = dict(wa_cmds)  # name -> cmd, removed once a counterexample lands
    ok = True
    start = time.perf_counter()
    probes = 0
    for k in range(iters):
        if not unresolved:
            break
        if (time.perf_counter() - start) * 1000.0 > budget_ms:
            break
        stdin_text = _run_generator(p, base_line, reseed=100003 + k)
        if stdin_text is None:
            continue
        probes += 1
        case = p.build_dir / "stress_case.txt"
        case.write_text(stdin_text)
        r_main = run(main_cmd, stdin_path=case, timeout_ms=tl)
        if r_main.exit_code != 0:
            continue
        ans = p.build_dir / "stress_ans.txt"
        ans.write_text(r_main.stdout)
        for name in list(unresolved):
            r_wa = run(unresolved[name], stdin_path=case, timeout_ms=tl)
            verdict_bad = False
            if r_wa.exit_code != 0:
                verdict_bad = True  # RE counts as distinguished
            else:
                out = p.build_dir / f"stress_out_{name}.txt"
                out.write_text(r_wa.stdout)
                chk = run([str(checker), str(case), str(out), str(ans)])
                verdict_bad = chk.exit_code != 0
            if verdict_bad:
                saved = found_dir / f"{Path(name).stem}.txt"
                saved.write_text(stdin_text)
                lines.append(
                    f"  ❌ {name} is AC on every fixed test, but random probe #{probes} "
                    f"BREAKS it — the fixed set missed this bug. Counterexample saved "
                    f"to _build/stress_found/{saved.name}; add it as a test "
                    f"(generator-agent), then this WA is legitimate.")
                del unresolved[name]
                ok = False
    for name in unresolved:
        lines.append(
            f"  ❌ {name} is AC on every fixed test AND no counterexample found in "
            f"{probes} random probes — it is probably NOT actually wrong. Either the "
            f"bug only bites at a scale/shape random search can't reach (make the "
            f"trap explicit), or delete it (solutions-agent).")
        ok = False

    head = "stress_correctness: " + ("PASS" if ok else "FAIL") + f" ({probes} probes)"
    return ok, head + "\n" + "\n".join(lines)


# --------------------------------------------------------------------------- #
def tle_search(problem_dir: Path) -> tuple[bool, str]:
    """Worst-case sweep proving each declared too-slow target is actually forced
    over the time limit by the adversarial patterns — searching seeds the fixed
    script didn't pin. SKIPs cleanly when the problem declares no too-slow
    target (legitimate for ad-hoc/math problems)."""
    p = Problem.load(problem_dir)
    targets = p.tle_target_files()
    declared = p.too_slow_targets or []

    if not targets and not declared:
        return True, "tle_search: SKIP (no too-slow targets declared for this problem)"

    if declared and not targets:
        return False, ("tle_search: FAIL — PROBLEM_SPEC/meta declares too-slow "
                       f"target(s) {[d.get('name', d) for d in declared]} but no "
                       "matching solutions/tle*.* file exists. solutions-agent must "
                       "ship one near-miss solution per declared target (§12.5).")

    adv_lines = _lines_for(p, "adversarial") or _lines_for(p, "max")
    if not adv_lines:
        return False, ("tle_search: FAIL — too-slow targets exist but no adversarial "
                       "generator line in script.txt to stress them. generator-agent "
                       "must add a worst-case pattern aimed at the target (§12).")

    checker = _checker_binary(p)
    tl = p.time_limit_ms
    n_seeds = int(p.stress_cfg("tle_seeds"))
    configs_cap = int(p.stress_cfg("tle_configs_cap"))
    min_ratio = float(p.stress_cfg("tle_target_min_ratio"))
    correct_max_ratio = float(p.stress_cfg("correct_max_ratio"))

    # Build the config list: each adversarial line as-is, then reseeded variants.
    configs: list[tuple[str, int | None]] = []
    for ln in adv_lines:
        configs.append((ln, None))
        for s in range(n_seeds):
            configs.append((ln, 900001 + s))
    configs = configs[:configs_cap]

    main_cmd = _runnable(p.solutions_dir / p.main_solution, p.build_dir)
    warmup(main_cmd)
    target_cmds = {f.name: _runnable(f, p.build_dir) for f in targets}
    for c in target_cmds.values():
        warmup(c)

    lines = []
    ok = True

    # (a) intended solution must stay comfortably under TL on every config.
    worst_main = 0.0
    main_cap = max(tl * 3, 3000)
    materialized: list[tuple[str, int | None, Path]] = []
    for ln, seed in configs:
        stdin_text = _run_generator(p, ln, seed)
        if stdin_text is None:
            continue
        case = p.build_dir / "tle_case.txt"
        case.write_text(stdin_text)
        r = run(main_cmd, stdin_path=case, timeout_ms=main_cap)
        if r.timed_out:
            ok = False
            lines.append(f"  ❌ intended solution {p.main_solution} TIMED OUT (>{main_cap}ms) "
                         f"on adversarial config `{ln}`" + (f" +seed {seed}" if seed else "") +
                         " — the intended solution can't meet its own limit on this "
                         "input; TL too tight or the solution is wrong (escalate).")
            continue
        frac = r.wall_ms / tl
        worst_main = max(worst_main, frac)
        # keep a materialized copy for target runs (avoid regenerating)
        keep = p.build_dir / f"tle_cfg_{len(materialized):02d}.txt"
        keep.write_text(stdin_text)
        materialized.append((ln, seed, keep))
    if worst_main > correct_max_ratio:
        ok = False
        lines.append(f"  ❌ intended solution worst case used {worst_main*100:.0f}% of the "
                     f"{tl}ms limit on a swept adversarial config (cap {correct_max_ratio*100:.0f}%) "
                     f"— too thin a margin; loosen TL or optimize the reference.")
    else:
        lines.append(f"  ✓ intended solution stayed ≤{worst_main*100:.0f}% of TL across "
                     f"{len(materialized)} adversarial configs")

    # (b) each too-slow target must be forced over the limit by SOME config.
    for name, cmd in target_cmds.items():
        worst = 0.0
        killer = None
        target_cap = max(int(tl * (min_ratio + 1.0)), tl + 1000)
        for ln, seed, case in materialized:
            r = run(cmd, stdin_path=case, timeout_ms=target_cap)
            if r.timed_out:
                worst = float("inf")
                killer = (ln, seed, target_cap)
                break
            worst = max(worst, r.wall_ms)
            if r.wall_ms >= tl * min_ratio and r.wall_ms > tl:
                killer = (ln, seed, r.wall_ms)
                break
        if killer is None:
            ok = False
            shown = "∞" if worst == float("inf") else f"{worst:.0f}ms"
            lines.append(
                f"  ❌ too-slow target {name}: NO swept adversarial config forced it over "
                f"the {tl}ms limit (worst {shown}). The trap is not enforced — the "
                f"current patterns/seeds can't kill it. generator-agent must build a "
                f"stronger worst-case (right shape AND large enough n), per §12.5.")
        else:
            ln, seed, val = killer
            shown = f">{val}ms (timeout)" if val == target_cap else f"{val:.0f}ms"
            lines.append(
                f"  ✓ too-slow target {name}: forced to {shown} (≥ {tl}ms limit) by "
                f"`{ln}`" + (f" +seed {seed}" if seed else "") +
                (" — adopt this seed in script.txt if the fixed test doesn't already "
                 "trigger it" if seed else ""))

    head = "tle_search: " + ("PASS" if ok else "FAIL")
    return ok, head + "\n" + "\n".join(lines)


if __name__ == "__main__":
    import sys
    d = Path(sys.argv[1])
    ok1, t1 = stress_correctness(d, matrix=None)
    ok2, t2 = tle_search(d)
    print(t1); print(); print(t2)
    sys.exit(0 if (ok1 and ok2) else 1)
