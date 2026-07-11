# Solution roster & WA bug taxonomy

Read by `solutions-agent`. 7 core + up to 3 justified additions (§13).

## Every WA/RE/TL file MUST declare its expected verdict
As the first ~10 lines of the file, in a comment, include a machine-checked
tag:
```
// EXPECTED_VERDICT: WA
```
(or `RE` / `TL` / `ML` / `RJ`; `#` comment for `.py`). `local_harness` parses
this and asserts the solution actually produces that verdict somewhere in the
matrix — not just "any non-AC verdict, for any reason." Without this, a WA
file that crashes on test 1 for an unrelated typo (not the bug you meant to
encode) would silently pass the local check as "non-AC somewhere," and the
label on the file would become decorative — the trap you thought you built
was never actually exercised. The tag makes that failure mode structurally
impossible to miss.

## Core (7)
| File | Role | Tag | EXPECTED_VERDICT |
|---|---|---|---|
| correct.py | reference | OK | (must be AC always — no tag needed) |
| correct.cpp | reference (C++) | MA | (must be AC always — no tag needed) |
| brute.cpp | naive-correct | TL | (must show AC+TL mix — no tag needed) |
| WA1.py | off-by-one/boundary | WA | `WA` |
| WA2.py | wrong greedy/invariant | WA | `WA` |
| WA3.py | overflow/precision/modulo | WA | `WA` |
| WA4.cpp | RTE/OOB or wrong-DS TLE+WA | RE | `RE` |

Exactly ONE `MA` (main). Others correct → `OK`.

**These four are the fallback taxonomy, not the starting point.** Before
reaching for them, `PROBLEM_SPEC.md`'s "Most Tempting Wrong Approach(es)"
section names the 1-2 ideas a strong competitor is actually most likely to
submit for THIS problem — at least one WA file must specifically target each
one named there. The generic off-by-one/greedy/overflow/RTE categories fill
any remaining roster slots, but a roster that's entirely generic (defeating
no problem-specific trap) is under-covering, even if it technically satisfies
the file count.

**If the problem is multitest**, strongly consider a WA that forgets to reset
global/static state (an array, a visited-flags buffer, an accumulator)
between test cases within one file — this is the single most common
multitest-specific bug in real CP, both as something contestants get wrong
and as something worth specifically testing for. It fits naturally as one of
the ≤3 optional additions, or can replace a generic entry when it's a more
relevant trap than what it replaces.

## Optional (≤3, must be distinct — not padding)
`brute2.cpp` (different inefficiency), `WA5.*` (complexity-class mistake that
bites at the constraints), `correct_alt.*` (different correct approach),
multitest-state-reset WA (see above). Additions must be justified, not
padding — `local_harness` flags near-total overlap in two WA files' failing
test sets as a signal to consolidate rather than pad.

## Discipline
- Each WA/brute file has a comment header naming the exact mistake and why it
  fails, PLUS the `EXPECTED_VERDICT` tag described above.
- **A WA file that fails nothing is a fixture bug**, not a deliverable — fix the
  file or add a test that exposes it. Same for a WA whose observed verdicts
  never include its declared `EXPECTED_VERDICT`.
- Overflow bugs that rely on native integer overflow belong in C++, not Python.
- Keep every WA/RE file's algorithmic complexity fast (`O(n)`-ish, not the
  brute's complexity) so its intended failure mode is the claimed one (WA/RE)
  and not TL. On Polygon, solution tags are strictly enforced at package
  build — a `WA`-tagged solution that times out instead fails the build.
- If the intended (`MA`) solution uses `unordered_map`/`unordered_set` keyed
  by input-derived values, either seed it with a randomized salt or note
  explicitly why hash-collision attacks don't apply here — and make sure
  generator-agent has an adversarial test targeting exactly that hash (see
  `tutorials/generator.md`).
- **The `MA` solution must be clean under ASan+UBSan**, not just `-O2` —
  `local_harness/sanitize_check.py` runs this automatically as part of the
  local self-check. `-O2` can hide undefined behavior (signed overflow,
  out-of-bounds reads, uninitialized reads) that "happens to work" on one
  machine/compiler and misbehaves on Polygon's actual judge; "it passed
  locally" is not evidence of UB-freedom.
- Verify locally (`local_harness/`) before declaring done: cross-check correct.py
  vs correct.cpp, confirm brute's partial-TLE pattern, confirm every WA is non-AC
  somewhere AND matches its declared `EXPECTED_VERDICT`.
