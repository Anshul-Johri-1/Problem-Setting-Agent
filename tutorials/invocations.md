# Invocations — verdict matrix & failure classification

Read by `reviewer-agent`. NOTE: Polygon exposes NO invocations API (verified live,
§9.4) — the backend is `polygon_client/invocations.py` (default: local harness).

## Expected verdict matrix (the "done" signal)
| Solution | Expected |
|---|---|
| correct.py / correct.cpp / correct_alt.* | AC on all tests |
| brute.cpp / brute2.cpp | AC small/medium tiers, TL max tier only |
| WA1–WA5 | WA/RE/TL on ≥1 test, never AC on all |

## Failure → fix-target
| Observed | Classification | Route to |
|---|---|---|
| Validator warning (unexercised boundary) | test-plan gap | generator-agent |
| **Correct solution WA/RE/TL anywhere** | **spec ambiguity / checker bug** | **ESCALATE_TO_HUMAN (no auto-patch)** |
| Brute passes everything | tests too weak | generator-agent (bigger/adversarial max) |
| Brute TLEs everywhere | small/medium too big | generator-agent (loosen tiers) |
| A WA solution passes everything | broken fixture | solutions-agent / generator-agent |
| Checker rejects valid alt output (custom) | checker bug | checker-agent |

## Loop discipline
- One patch → one responsible tab → one commit (§11) → re-run.
- Cap at `retry_cap` (org_defaults.yaml, default 5) → then ESCALATE_TO_HUMAN.
- A correct solution failing is NEVER auto-patched — it signals a spec-level
  problem the human must resolve (§1.5).
- Report the verdict matrix verbatim into the audit trail.
