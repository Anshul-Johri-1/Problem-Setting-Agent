# Workflow Guidelines (condensed)

The operational reference for the pipeline. Section numbers (§) point at the
full build spec.

## Non-negotiable guardrails (§1)
1. No generation / file writes / Polygon calls before the human approves
   `PROBLEM_SPEC.md`. Enforced in code by `orchestrator/dispatch.py` + `gate.py`.
2. No commit with unclean local self-checks (§10).
3. No package build with a dirty working copy or unclean invocations.
4. Credentials never enter agent context — only `orchestrator/cli.py` loads
   `.env` for a live call.
5. A correct solution getting WA/RE/TL/ML halts → `ESCALATE_TO_HUMAN`; never
   auto-patch.
6. Spec/constraint changes mid-pipeline are patch requests to the human.
7. Retry loops capped at `retry_cap` (default 5).
8. **No ad hoc scripts against `polygon_client`/`orchestrator` internals.**
   `python3 -m orchestrator.cli` is the only sanctioned way to touch live
   Polygon — see `.claude/GUARDRAILS.md` for why this is a hard rule, not a
   suggestion (an agent bypassed everything above it once, by doing exactly
   this).

## The one gate (§6) — and why it's checked twice
`state.json` per problem tracks pipeline state. The dispatcher refuses (in code)
to run any generation-stage agent unless state is post-approval — but that only
protects calls that go through `dispatch()`. `orchestrator/uploader.py`'s
`PolygonUploader` independently re-checks the state.json AUDIT TRAIL (not just
the current state value) before every single live call, so code that skips
`Orchestrator` entirely and drives `PolygonUploader` directly is still refused.
spec-agent is the only pre-approval agent. Run `python3 tests/test_gate.py` and
`python3 tests/test_cli.py` to see both layers enforced.

## State path (§7)
```
DRAFTING_SPEC → AWAITING_APPROVAL → APPROVED → GENERATING_ARTIFACTS
→ LOCAL_SELF_CHECK → UPLOADING_STATEMENT → UPLOADING_VALIDATOR
→ UPLOADING_CHECKER → UPLOADING_TESTS → UPLOADING_SOLUTIONS → SETTING_LIMITS
→ RUNNING_INVOCATIONS → FINAL_COMMIT → BUILDING_PACKAGE → LINK_READY
```
Bounce-backs: local-check → regen; invocations → responsible tab. Escalation
reachable from anywhere.

## Fixed org rules (`config/org_defaults.yaml`)
≤15 test files · 7–10 solutions · ≥3 generators · ≥10 validator stress tests ·
multitest preferred · standard-checker-first · optional access-grant reminder
(empty by default) · retry cap 5. The human may suggest a test/solution/
generator count in `/create-problem`; spec-agent honors it if it fits these
bounds, else clamps and flags the clamp for approval.

## Tab-by-tab commits (§11)
statement → validator → checker → tests → solutions → limits → (invocations) →
final. Each its own reviewed commit. Patches re-commit at the responsible tab.

## Checker choice (§14)
Standard by default (`config/standard_checkers.yaml`, live-verified). Custom
only when the answer isn't unique.

## Solution roster (§13)
7 core (correct.py, correct.cpp, brute.cpp, WA1–WA4) + ≤3 justified additions.
Exactly one `MA`. Every WA must fail somewhere or it's a fixture bug.

## Generators & tiers (§12)
edge / random / adversarial, argv-driven. Compute the n-threshold; brute must
show a PARTIAL TLE pattern. ≤15 files, T-format multitest preferred.

## Invocation loop (§15)
reviewer-agent classifies the verdict matrix and routes each patch to one
upstream agent. Correct-solution failure or retry-cap exhaustion → escalate.

## Final output (§17)
Polygon link + revision summary + checker + solution/test counts + clean
invocation summary + the manual access-grant reminder, only if any are
configured in `org_defaults.yaml`.
