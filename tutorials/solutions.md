# Solution roster & WA bug taxonomy

Read by `solutions-agent`. 7 core + up to 3 justified additions (§13).

## Core (7)
| File | Role | Tag | Expected |
|---|---|---|---|
| correct.py | reference | OK | AC all |
| correct.cpp | reference (C++) | MA | AC all |
| brute.cpp | naive-correct | TL | AC small/medium, TL max only |
| WA1.py | off-by-one/boundary | WA | non-AC ≥1 |
| WA2.py | wrong greedy/invariant | WA | non-AC ≥1 |
| WA3.py | overflow/precision/modulo | WA | non-AC ≥1 |
| WA4.cpp | RTE/OOB or wrong-DS TLE+WA | RE | non-AC ≥1 |

Exactly ONE `MA` (main). Others correct → `OK`.

## Optional (≤3, must be distinct — not padding)
`brute2.cpp` (different inefficiency), `WA5.*` (complexity-class mistake that
bites at the constraints), `correct_alt.*` (different correct approach).

## Discipline
- Each WA/brute file has a comment header naming the exact mistake and why it
  fails. `reviewer-agent` checks behavior against this header.
- **A WA file that fails nothing is a fixture bug**, not a deliverable — fix the
  file or add a test that exposes it.
- Overflow bugs that rely on native integer overflow belong in C++, not Python.
- Verify locally (`local_harness/`) before declaring done: cross-check correct.py
  vs correct.cpp, confirm brute's partial-TLE pattern, confirm every WA is non-AC
  somewhere.
