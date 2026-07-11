# Generator design & tier plan

Read by `generator-agent`. Reference: Codeforces generators tutorial (entry 18291).

## Three generators, distinct purposes (§12)
- `generator_edge.cpp` — deterministic boundaries (`--case=...`). Small.
- `generator_random.cpp` — uniform random, small→medium (`-n -seed`).
- `generator_adversarial.cpp` — worst case at max n (`-n -pattern -seed`).
Each is flag/argv-driven. testlib seeds RNG from the full argv, so vary args
(especially `-seed`) to get distinct tests. Add a 4th only for a truly distinct
pattern.

## n-threshold (compute, then honor)
```
n_threshold ≈ (time_limit_ms × ops_per_ms) ^ (1 / brute_exponent)
```
`ops_per_ms ≈ 1e5..1e6` depending on constant factor; state your assumption.
This must match spec-agent's Test-Tier Plan preview (the human approved it).

## Tiers (total ≤ 15 files)
1. Samples — 1–2, verbatim from the prompt.
2. Edge — 3–4, small (brute trivially passes).
3. Small-random stress — 2–3, low n (correctness vs correct.cpp).
4. Medium/boundary — 2–3, n near threshold (brute approaches TL).
5. Max/adversarial — 3–4, max n (brute reliably exceeds the cap).

Prefer **T-format multitest** packing within each file. The distribution must
give brute a PARTIAL TLE pattern (§0): passes small/medium, times out on max.

## Script
`script.txt`: one line per test, e.g. `gen_random -n 2000 -seed 2`. Confirm the
Polygon script-line-per-test model / FreeMarker loop syntax against §18 item 6.
