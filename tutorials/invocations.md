# Build-failure classification

Read by `reviewer-agent`. Polygon exposes NO invocations API (verified live,
§9.4) — there is no per-test verdict matrix to read, ever. The only signal is
`problem.buildPackage(full, verify=True)`'s terminal state (`READY`/`FAILED`)
plus the free-text `comment` on `problem.packages`, surfaced by
`orchestrator/pipeline.py::build_and_verify` as a `BuildFailure`. That build is
still a real judge run — Polygon compiles and runs every solution against
every test and strictly enforces each one's declared tag (live-verified: a
full roster build correctly flagged MA/OK/TL/WA mismatches by name) — the
comment just reports it at build granularity, not per-test.

## Expected tag behavior (the "done" signal)
| Solution tag | Expected on Polygon's build |
|---|---|
| `MA` / `OK` (correct.py / correct.cpp / correct_alt.*) | AC on all tests |
| `TL` (brute.cpp / brute2.cpp / TLE1–TLEk) | brute: AC small/medium, TL max tier only. TLE\*: AC on small tier, TL on the adversarial shape aimed at each near-miss |
| `WA` / `RE` / `ML` / `RJ` | that verdict on ≥1 test, never AC on all |

## Failure → fix-target
| Comment implies | Classification | Route to |
|---|---|---|
| A validator rejected a VALID test or accepted an INVALID one | test-plan / validator bug | validator-agent |
| **Comment implicates `MA` or another `OK`-tagged solution** | **spec ambiguity / checker bug / limit set too tight** | **already escalated in code before reviewer-agent runs (§1.5) — `classify_build_failure`** |
| Brute passes everything | tests too weak | generator-agent (bigger/adversarial max) |
| **A too-slow target (`TL`-tagged TLE\*) is never forced over the limit** | **the core hole — adversarial tier too weak for the near-miss** | **generator-agent (build a stronger worst-case shape/size, ≥5–10× over TL by construction per §12.5)** |
| Brute TLEs everywhere | small/medium too big | generator-agent (loosen tiers) |
| A `WA`/`RE`/`ML`/`RJ`-tagged solution passed everything | broken fixture, or the test set is too weak to expose the bug | solutions-agent (sharpen the bug) or generator-agent (add the input shape from the spec's named trap) |
| A `WA`/`RE`/`ML`/`RJ`-tagged solution produced a different violating verdict than its tag | mislabeled fixture — failing, but not for the claimed reason | solutions-agent (fix the bug or the tag) |
| Checker rejects a valid alt output (custom) | checker bug | checker-agent |

## Loop discipline
- One patch → re-run `orchestrator.cli finish`. `upload()` is idempotent — it
  re-sends every tab (cheap API calls, no local execution) rather than
  tracking which single tab changed, so this is always safe.
- Cap at `retry_cap` (org_defaults.yaml, default 5) → then `ESCALATE_TO_HUMAN`,
  enforced in code by `build_and_verify()`.
- A build failure implicating a reference (`MA`/`OK`-tagged) solution is NEVER
  auto-patched — it signals a spec-level problem the human must resolve
  (§1.5), and code escalates it before reviewer-agent is even dispatched.
- Report the comment verbatim into the audit trail.
