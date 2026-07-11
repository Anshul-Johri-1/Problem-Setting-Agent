---
name: solutions-agent
description: Post-approval only. Produces the 7–10 file solution roster (correct, brute, and WA/RE/TL variants), each targeting a named problem-specific trap where possible, each locally verified to fail for its declared reason. A WA file that fails nothing — or fails for the wrong reason — is a bug, not a deliverable.
tools: Read, Write, Edit, Bash
---

# solutions-agent

Input: approved `PROBLEM_SPEC.md` + `tutorials/solutions.md` +
`templates/solutions/`. Output: 7–10 files in `problems/<name>/solutions/`,
matching the count `PROBLEM_SPEC.md`'s Solution Roster preview settled on
(reflecting any `num_solutions` the human suggested, already clamped to the
7–10 org range by spec-agent) — don't add or drop files beyond what was
previewed and approved.

## Start from the spec's named traps, not the generic taxonomy
`PROBLEM_SPEC.md`'s "Most Tempting Wrong Approach(es)" section names the 1-2
ideas a strong competitor is most likely to submit for THIS problem. At least
one WA file must specifically target each one named there — build these
first. The generic fixed core below fills remaining roster slots; it's the
fallback, not the starting point.

## Too-slow targets are first-class solutions, not "the brute" (§12.5)
`PROBLEM_SPEC.md`'s "Most Tempting Too-Slow Approach(es)" / `meta.json`'s
`too_slow_targets` names the near-correct-but-slow submissions this problem
must reject — the intended algorithm with a fatal inefficiency (Dijkstra
without the stale-skip, a plain `queue`, `unordered_map` under collision, DP
without memo). Ship **one `TLE1.cpp`, `TLE2.cpp`, … per named target**:
- It implements the intended *algorithm* faithfully except for the one flaw,
  so it is **AC on the small tier** — that's what makes it a realistic
  competitor submission and not just another brute. `brute.cpp` stays the
  asymptotically-naive oracle; `TLE*` is a subtle near-miss. Keep both.
- Tag `EXPECTED_VERDICT: TL`, upload tag `TL`. It must be forced OVER the limit
  by the adversarial tier — `local_harness.stress.tle_search` sweeps generator
  seeds to prove exactly that, and the local check is RED until it does. If it
  isn't killed, the *test set* is too weak (tell generator-agent the input
  shape from the spec), not the solution.
- These do NOT count against needing WA files — a too-slow target is about
  timing, a WA is about correctness; a strong roster has both.

## Fixed core (7, §13)
```
correct.py   – reference, AC everywhere
correct.cpp  – same algorithm in C++, cross-validates correct.py
brute.cpp    – correct but naive; AC on small/medium, TL on max tier
WA1.py       – off-by-one / boundary
WA2.py       – wrong greedy / wrong invariant (algorithmically wrong)
WA3.py       – overflow / precision / modulo
WA4.cpp      – uninitialized/OOB RTE, or wrong DS giving TLE+WA mix
```
If the problem is multitest, consider swapping one generic slot for a WA that
forgets to reset global/static state between test cases — the single most
common real multitest-specific bug.

## Optional (≤3, only if genuinely distinct)
`brute2.cpp` (different inefficiency), `WA5.*` (complexity-class mistake that
bites at the given constraints), `correct_alt.*` (different correct approach for
extra cross-validation), a multitest-state-reset WA. Additions must be
justified, not padding — the harness flags near-total overlap between two
WA files' failing-test sets as a signal to consolidate.

## Every WA/RE file needs an EXPECTED_VERDICT tag
As one of the first ~10 lines: `// EXPECTED_VERDICT: WA` (C++) or
`# EXPECTED_VERDICT: WA` (Python), value ∈ `WA`/`RE`/`TL`/`ML`/`RJ`.
`local_harness` checks the solution's observed verdicts actually include this
value — "non-AC somewhere, for any reason" is not sufficient; the failure has
to match what you claimed. If it doesn't, the fixture is broken even if it
technically fails *something* — fix the bug or the tag until they agree.

## Rules (§8.5)
- Every WA/brute file carries a **comment header** stating exactly which mistake
  it encodes and why it's expected to fail, plus the `EXPECTED_VERDICT` tag.
- Tag mapping for upload: `MA` on the one true main (`correct.cpp` or
  `correct.py`), `OK` on other corrects, `TL`/`WA`/`RE` on the rest.
- Keep WA/RE files algorithmically fast (not the brute's complexity) so they
  fail with their claimed verdict, not TL — Polygon strictly enforces
  solution tags at package build.
- If the `MA` solution uses `unordered_map`/`unordered_set` keyed by
  input-derived values, either add a randomized salt or explain in a comment
  why hash-collision attacks don't apply, and flag it to generator-agent so an
  adversarial test targets that hash specifically.
- **Locally verify before declaring done** (`local_harness/`): correct.* AC on
  all tests AND clean under ASan+UBSan (`sanitize_check.py` — `-O2` can hide
  undefined behavior that misbehaves on Polygon's actual judge, so "passed
  locally" isn't evidence of UB-freedom); brute shows the partial-TLE pattern;
  each `TLE*` target is AC on small AND forced over the limit by the
  adversarial tier (`stress.tle_search` — RED until it is); each WA produces
  its declared `EXPECTED_VERDICT`. A WA that fails nothing, or fails with a
  DIFFERENT verdict than declared, is a fixture bug — fix the file or the
  tests, don't ship it. A WA that is AC on every fixed test but breaks under
  `stress_correctness`'s random search means the *tests* missed its bug: adopt
  the saved counterexample as a real test.
- brute must never TLE on everything nor AC on everything (§0).
