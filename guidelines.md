# Workflow Guidelines (condensed)

The operational reference for the pipeline. Section numbers (§) point at the
full build spec.

## Non-negotiable guardrails (§1)
1. No generation / file writes / Polygon calls before the human approves
   `PROBLEM_SPEC.md`. Enforced in code by `orchestrator/dispatch.py` + `gate.py`.
2. There is no local self-check. Nothing compiles or runs any
   solution/generator/validator/checker locally — Polygon's own
   `buildPackage(verify=True)` (triggered by `orchestrator.cli finish`) is the
   one verification gate.
3. No package build with a dirty working copy — `upload()` always runs
   immediately before `build_and_verify()`, never separately.
4. Credentials never enter agent context — only `orchestrator/cli.py` loads
   `.env` for a live call.
5. A build failure implicating the MA/a reference (`OK`-tagged) solution, or a
   sample-output mismatch, halts → `ESCALATE_TO_HUMAN`; never auto-patch.
   Enforced in code (`orchestrator/reviewer.py::classify_build_failure`,
   `orchestrator/pipeline.py::verify_samples`).
6. Spec/constraint changes mid-pipeline are patch requests to the human.
7. Retry loops capped at `retry_cap` (default 5), enforced by
   `build_and_verify()` via `StateStore.bump_retry()`.
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
→ UPLOADING_STATEMENT → UPLOADING_VALIDATOR → UPLOADING_CHECKER
→ UPLOADING_TESTS → UPLOADING_SOLUTIONS → SETTING_LIMITS → FINAL_COMMIT
→ BUILDING_PACKAGE (Polygon's buildPackage(verify=True) — the one
  verification gate) → SAMPLE_VERIFY → LINK_READY
```
Bounce-back: `BUILDING_PACKAGE → GENERATING_ARTIFACTS` on a routable build
failure (patch, then re-run `finish` — `upload()` is idempotent). Escalation
reachable from anywhere.

## Fixed org rules (`config/org_defaults.yaml`)
≤15 test files · 7–10 solutions · ≥3 generators · ≥10 validator stress tests ·
multitest preferred · standard-checker-first · optional access-grant reminder
(empty by default) · retry cap 5. The human may suggest a test/solution/
generator count in `/create-problem`; spec-agent honors it if it fits these
bounds, else clamps and flags the clamp for approval.

## Tab-by-tab commits (§11)
statement → validator → checker → tests → solutions → limits → final commit →
build. Each its own commit. `upload()` is idempotent — a patch after a build
failure just re-runs the whole sequence, safely.

## Checker choice (§14)
Standard by default (`config/standard_checkers.yaml`, live-verified). Custom
only when the answer isn't unique.

## Solution roster (§13)
7 core (correct.py, correct.cpp, brute.cpp, WA1–WA4) + ≤3 justified additions.
Exactly one `MA`. Every WA must fail somewhere or it's a fixture bug.

## Too-slow targets (§12.5) — the quality bar
For each near-correct-but-slow approach the spec names (Dijkstra without the
stale-skip, plain `queue`, default-hash `unordered_map`, DP without memo), ship
a `TLE*` solution tagged `TL` that AC's the small tier and MUST be forced over
the limit by an adversarial shape aimed at *it* (not at the naive brute).
There is no local sweep to prove this — `buildPackage(verify=True)` is the
enforcement, and the build FAILS (naming the file) until each is actually
killed on Polygon's own judge. This is what makes "queue-instead-of-heap
Dijkstra gets TLE" a guarantee, not a hope. Empty is legitimate only when the
spec explicitly says no near-miss exists.

## Generators & tiers (§12)
edge / random / adversarial, argv-driven. Estimate the n-threshold algebraically,
then reason it through structurally (operation counts, constant factors — no
local timing run to calibrate against) and size the max tier so the intended
solution is comfortably under TL and every too-slow target is comfortably
(≥5–10×) over by construction. brute AND each `TLE*` must show a PARTIAL TLE
pattern. ≤15 files (soft — raise with the human if distinct max shapes don't
fit), T-format multitest preferred except for max-n cases.

## Build-and-verify (§15) — the one verification gate
No local execution anywhere. `orchestrator.cli finish` uploads every tab, then
triggers Polygon's `buildPackage(verify=True)`: Polygon itself compiles and
runs every solution against every test with strict per-tag enforcement — a WA
file that turns out AC everywhere, or a too-slow target that never TLEs, fails
the build by name, same as a broken validator or checker. reviewer-agent
classifies the failure comment and routes the patch to one upstream agent;
`upload()` is idempotent so re-running `finish` after the patch is always
safe. A failure implicating the MA/a reference solution, a sample-output
mismatch, or retry-cap exhaustion → escalate (code-enforced, never a judgment
call).

## Final output (§17)
Polygon link + revision summary + checker + solution/test counts + clean
invocation summary + the manual access-grant reminder, only if any are
configured in `org_defaults.yaml`.
