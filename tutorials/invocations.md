# Invocations — verdict matrix & failure classification

Read by `reviewer-agent`. NOTE: Polygon exposes NO invocations API (verified live,
§9.4) — the backend is `polygon_client/invocations.py` (default: local harness).

## Expected verdict matrix (the "done" signal)
| Solution | Expected |
|---|---|
| correct.py / correct.cpp / correct_alt.* | AC on all tests |
| brute.cpp / brute2.cpp | AC small/medium tiers, TL max tier only |
| TLE1–TLEk (too-slow targets, §12.5) | AC on small tier, TL on the adversarial shape aimed at each near-miss |
| WA1–WA5 | WA/RE/TL/ML on ≥1 test, matching each file's declared `EXPECTED_VERDICT`, never AC on all |

## Failure → fix-target
| Observed | Classification | Route to |
|---|---|---|
| Validator warning (unexercised boundary) | test-plan gap | generator-agent |
| **Correct solution WA/RE/TL/ML anywhere** | **spec ambiguity / checker bug / limit set too tight** | **ESCALATE_TO_HUMAN (no auto-patch)** |
| Brute passes everything | tests too weak | generator-agent (bigger/adversarial max) |
| **A too-slow target (TLE*) is never forced over the limit** | **the core hole — adversarial tier too weak for the near-miss** | **generator-agent (build the defeating shape; stress.tle_search sweeps seeds to confirm)** |
| Brute TLEs everywhere | small/medium too big | generator-agent (loosen tiers) |
| WA passes every fixed test but stress_correctness breaks it | tests missed the bug | generator-agent (adopt saved counterexample) |
| A WA solution passes everything | broken fixture | solutions-agent / generator-agent |
| A WA/RE solution's observed verdicts never include its declared `EXPECTED_VERDICT` | mislabeled fixture — failing, but not for the claimed reason | solutions-agent (fix the bug or the tag) |
| Checker rejects valid alt output (custom) | checker bug | checker-agent |

## Loop discipline
- One patch → one responsible tab → one commit (§11) → re-run.
- Cap at `retry_cap` (org_defaults.yaml, default 5) → then ESCALATE_TO_HUMAN.
- A correct solution failing is NEVER auto-patched — it signals a spec-level
  problem the human must resolve (§1.5).
- Report the verdict matrix verbatim into the audit trail.
