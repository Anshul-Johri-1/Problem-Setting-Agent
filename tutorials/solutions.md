# Solution roster & WA bug taxonomy

Read by `solutions-agent`. 7 core + up to 3 justified additions (§13).

## Every solution's Polygon tag IS its declared verdict — no separate local tag
There is no local judge run and no `EXPECTED_VERDICT` comment convention
anymore. Declare each file's intended Polygon tag directly in `meta.json`'s
`solution_tags`; `Problem.tag_for()` reads it. `buildPackage(verify=True)`
strictly enforces that tag against the file's real behavior on Polygon's own
judge and fails the build by name if it doesn't match — that live enforcement
IS the check that used to run locally. Still write a comment header stating
the mistake each file encodes (good documentation), it's just no longer
machine-parsed.

## Core (7)
| File | Role | Tag |
|---|---|---|
| correct.py | reference | OK |
| correct.cpp | reference (C++) | MA |
| brute.cpp | naive-correct | TL |
| WA1.py | off-by-one/boundary | WA |
| WA2.py | wrong greedy/invariant | WA |
| WA3.py | overflow/precision/modulo | WA |
| WA4.cpp | RTE/OOB or wrong-DS TLE+WA | RE |

Exactly ONE `MA` (main). Others correct → `OK` — including `correct_alt.*` if
you ship one; it's a real roster file now, not a local-only cross-check
(Polygon's build fails an `OK` solution that disagrees with the checker/MA on
any test, which is how a second-reference disagreement gets caught).

## Too-slow targets (§12.5) — the near-miss, not the brute
For every entry in `PROBLEM_SPEC.md`'s "Most Tempting Too-Slow Approach(es)",
ship a `TLE1.cpp` / `TLE2.cpp` / … that implements the intended **algorithm**
with exactly that one fatal inefficiency:

| File | Role | Tag |
|---|---|---|
| TLE1.cpp | intended algorithm minus one optimization (e.g. Dijkstra without the `if d > dist[u]: continue` stale-skip; plain `queue`; default-hash `unordered_map`) | TL |

The distinction from `brute.cpp` matters and both exist:
- `brute.cpp` is asymptotically naive (O(n²) where intended is O(n log n)) — a
  correctness oracle that's easy to kill with any max test.
- `TLE*` is the *same asymptotic class or one log off* — it AC's the small tier
  and only a **specifically-shaped** adversarial input forces it over. That
  input shape is named in the spec; if you can't make the target TLE, the test
  set is wrong, not the solution (route to generator-agent).

This is the whole reason the pipeline exists: a `queue`-instead-of-heap Dijkstra
that would get AC on a line graph must get TLE here. There's no local sweep to
prove that anymore — `buildPackage(verify=True)` is the enforcement; a `TL`-
tagged `TLE*` that doesn't actually TLE fails the build by name.

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
bites at the constraints), `correct_alt.*` (different correct approach, tagged
`OK`), multitest-state-reset WA (see above). Additions must be justified, not
padding.

## Discipline
- Each WA/brute/TLE file has a comment header naming the exact mistake and
  why it fails.
- **A WA file that turns out AC everywhere on Polygon's build is a fixture
  bug**, not a deliverable — fix the file or add a test that exposes it. Same
  for a WA whose actual verdict doesn't match its declared tag.
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
- There is no local compile/run of any solution and no ASan/UBSan pass —
  nothing in this pipeline executes anything locally. Write each solution to
  be correct (or wrong in exactly the declared way) on inspection; Polygon
  compiling and running the whole roster at `buildPackage(verify=True)` is
  the only verification, and it's strict about tags. A build failure names
  the offending solution; fix it or its declared tag once that happens, don't
  try to pre-verify locally.
