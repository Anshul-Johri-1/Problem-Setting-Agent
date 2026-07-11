# Generator design & tier plan

Read by `generator-agent`. Reference: Codeforces generators tutorial (entry 18291).

## Three generators, distinct purposes (§12)
- `generator_edge.cpp` — deterministic boundaries (`--case=...`). Small.
- `generator_random.cpp` — uniform random, small→medium (`-n -seed`).
- `generator_adversarial.cpp` — worst case at max n (`-n -pattern -seed`).
Each is flag/argv-driven. testlib seeds RNG from the full argv, so vary args
(especially `-seed`) to get distinct tests. Add a 4th only for a truly distinct
pattern — with two required exceptions below, which are NOT optional even
though they'd otherwise count as "just" a 4th pattern.

### Required: hash-collision test, if the intended solution plausibly hashes
If `PROBLEM_SPEC.md`'s Intended Solution uses (or a strong competitor's
solution would plausibly use) `unordered_map`/`unordered_set` keyed by
input-derived values, the adversarial generator MUST include a pattern that
targets that hash specifically — sequential or low-entropy keys chosen to
collide under the standard library's default hash, blowing up an
`unordered_map`'s buckets from O(1) to O(n) per operation. This is not
optional generator-agent improvisation; it's required whenever hashing is in
play, because a weak-hash submission that would get hacked in a real contest
should also fail in this pipeline's own local judging, not slip through
because the adversarial test happened to use large random values instead.

### Required checklist for graph/tree-shaped problems
Three generic generators (edge/random/adversarial) are not enough shape
coverage for a graph or tree problem — at minimum, cover these canonical
adversarial topologies across your edge/adversarial generators before
considering the tier plan complete:
- **star** (one hub, all others degree 1) — punishes anything assuming
  balanced degree.
- **path/chain** (a straight line) — punishes recursion depth (stack
  overflow) and anything assuming logarithmic tree height.
- **balanced** (e.g. complete binary tree) — the "well-behaved" case;
  necessary but not sufficient on its own.
- **disjoint components** (if the problem allows a non-connected graph) —
  punishes code that silently assumes connectivity.
This checklist applies in addition to, not instead of, the standard 5-tier
size/scale plan below.

## Too-slow targets: aim the adversary at the near-miss, not the brute (§12.5)
The naive `brute.cpp` (O(n²) where intended is O(n log n)) dies on *any* max-n
test — killing it proves nothing. The valuable, hard test is the one that
separates the intended solution from a **near-correct-but-slow** submission a
strong competitor actually writes. `PROBLEM_SPEC.md` names these under "Most
Tempting Too-Slow Approach(es)", each with the input SHAPE that defeats it, and
solutions-agent ships one `TLE*` file per target. Build one adversarial
`-pattern` per target, using that shape.

**Worked example — Dijkstra.** The near-misses are (a) Dijkstra without
`if d > dist[u]: continue` (processes stale heap entries) and (b) a plain
`queue` instead of a priority queue. The instinct is "max-n graph" — but:
- A **line/path graph** (`1—2—3—…—n`) maxes out *Bellman-Ford* (n−1
  iterations), so it's the right anti-test for the brute — yet each node
  relaxes exactly **once**, so the stale-check-less Dijkstra never re-pops
  anything and runs in clean O(m log m). The line graph gives it **AC**. This
  is the trap: the obvious "adversarial" test is useless against the bug you
  care about.
- To force the stale-check blow-up you need **many relaxations per node**: a
  layered/dense construction where a node's distance improves repeatedly (e.g.
  a fan of parallel paths with strictly decreasing totals, or a near-complete
  graph with adversarial weights), so the bad implementation pushes and pops
  each vertex Θ(deg) times → Θ(m·something) → TLE.

If you cannot make a declared target TLE, the shape is wrong — go back to the
spec's stated defeating shape; do not weaken the target or delete it.
`stress.tle_search` sweeps your adversarial seeds and is RED until every
declared target is forced over the limit, so this is enforced, not advisory.

## n-threshold: estimate algebraically, then MEASURE
```
n_threshold ≈ (time_limit_ms × ops_per_ms) ^ (1 / brute_exponent)
```
`ops_per_ms ≈ 1e5..1e6` depending on constant factor — but this is a **starting
estimate**, not the final size. For cache-bound work (graphs, DS) the real
separation is empirical. Run `python3 -m local_harness.stress <dir>` to see
measured runtimes of the intended solution and each `TLE*` target at your
candidate sizes, and **size the max tier from that measurement**: intended
comfortably under TL, every too-slow target comfortably (≥5–10×, see below)
over. State your final sizes; they must still match spec-agent's Test-Tier Plan
preview the human approved (if measurement forces a material change, that's a
patch request to the human, §1.6).

### Margin discipline
Local timing can't tell a 1.5× overshoot from noise, and Polygon's judge is a
different box. Build every too-slow anti-test so the target is **many× over TL
(aim 5–10×), never barely over** — a marginal local TLE becomes an AC on the
real judge. Keep the intended solution ≤~70% of TL on the same inputs so it has
headroom the other way.

## Tiers (total ≤ 15 files)
1. Samples — 1–2, verbatim from the prompt.
2. Edge — 3–4, small (brute AND every too-slow target trivially pass).
3. Small-random stress — 2–3, low n (correctness vs correct.cpp — this is also
   what `stress_correctness` searches for WA holes).
4. Medium/boundary — 2–3, n near threshold.
5. Max/adversarial — 3–4, max n, one shape per too-slow target (brute AND each
   `TLE*` reliably exceed the cap).

Prefer **T-format multitest** packing within each file — but max-n adversarial
cases can't be packed (one big case per file), so several distinct max shapes
may push the file count; if the shapes genuinely don't fit ≤15, raise it with
the human rather than dropping a needed anti-test. The distribution must give
both the brute and every declared too-slow target a PARTIAL TLE pattern (§0):
AC on small/medium, TL on the max shape aimed at them.

## Script
`script.txt`: one line per test, e.g. `gen_random -n 2000 -seed 2`. Confirm the
Polygon script-line-per-test model / FreeMarker loop syntax against §18 item 6.
