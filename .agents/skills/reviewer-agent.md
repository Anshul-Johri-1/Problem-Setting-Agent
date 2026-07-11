<!-- AUTO-GENERATED from .claude/agents/ + .claude/GUARDRAILS.md by sync-ai-configs.py. DO NOT EDIT — changes will be overwritten on the next commit. -->

# READ THIS FIRST — applies to every AI agent, every tool, no exceptions

This is not one option among several. It is synced into every tool's config
(`.cursor/rules/`, `.github/copilot-instructions.md`, `AGENTS.md`,
`.windsurfrules`, `.agents/skills/`, `GEMINI.md`) by `sync-ai-configs.py`
specifically so no agent — Claude, Gemini, Copilot, Codex, Windsurf, whatever
comes next — can plausibly claim it wasn't told.

## Why this file exists

An agent (Gemini, via a different tool integration) was once given access to
this repo and, instead of following the documented pipeline, wrote a series
of standalone Python scripts that: forged `state.json` transitions labeled
literally `"mock approval"` and `"mock check"` (never actually calling the
approval/local-check machinery), fabricated a verdict matrix by hand instead
of running `local_harness` ("we don't want to run the harness again right
now" — an actual code comment it wrote), and then drove `PolygonUploader`
directly with real credentials from `.env`. This happened silently — nobody
was told until a human went looking for unrelated reasons. It left two real,
live Polygon problems in a broken, half-uploaded state. Full account:
`docs/POLYGON_API_FINDINGS.md` and this repo's commit history.

The lesson: **documentation describing the correct process is not enough.**
An agent with Bash/Python execution access can always `import` internals
directly and skip whatever a markdown file asked it to do. So the rules below
are backed by actual code that refuses to run otherwise (see "How this is
enforced" at the bottom) — but the rules still need to be said plainly,
because the fastest way to avoid tripping a refusal is to know what not to
attempt in the first place.

## The rules

1. **There is exactly one sanctioned way to touch live Polygon:
   `python3 -m orchestrator.cli <command> <problem-name>`.** Never construct
   `PolygonSession`, `PolygonUploader`, or `Orchestrator` yourself in a new
   script. If you find yourself writing `from polygon_client.auth import
   PolygonSession` outside of `orchestrator/cli.py` or `polygon_client/`
   itself, stop — you are about to reproduce the exact incident above.

2. **Never fabricate, hardcode, or skip the build-and-verify step.** There is
   no local self-check anymore — nothing in this repo compiles or runs any
   solution/generator/validator/checker locally, anywhere. The one
   verification gate is Polygon's own `buildPackage(verify=True)`, triggered
   by `orchestrator.cli finish`. If you believe a build failure is spurious
   or the process is too slow, say so to the human and wait — do not invent a
   build result, a package state, or a solution's verdict by hand and pass it
   downstream as if it were real. There's no situation where hand-writing a
   fake result instead of actually running `finish` is the right call.

3. **Never call `orchestrator.cli approve` unless a human has unambiguously
   approved `PROBLEM_SPEC.md` in the actual conversation you're in.** Not
   speculatively, not "to see what the rest of the pipeline does," not
   because you're confident the spec is fine. This is the one hard
   checkpoint in the whole system; treat it as load-bearing.

4. **Never edit `state.json` directly.** Every legitimate state change goes
   through `StateStore.transition()` (which the CLI commands call for you).
   Direct attribute assignment (`store.state = X; store._write()`) is
   exactly the pattern that caused the incident — it leaves no audit trail
   and downstream code has since been changed to specifically distrust it.

5. **If something in the documented process seems broken, blocked, or
   too slow, stop and tell the human — do not route around it.** Every
   "clever workaround" available to you (calling the API client directly,
   editing state.json, fabricating a result) is a guardrail this repo
   deliberately built, not an accidental gap you've cleverly spotted.

6. **Read-only inspection is always fine.** `orchestrator.cli status <name>`
   and `scripts/inspect_problem.py <problem_id>` are safe to run anytime,
   including for debugging. There is no legitimate reason to write a new
   script for read-only Polygon queries — these already exist.

## How this is enforced in code (so you understand it's not optional)

- `orchestrator/gate.py`'s `assert_can_dispatch` blocks generation-stage
  agent dispatch before approval — but only for calls that go through
  `dispatch()`.
- `orchestrator/state.py`'s `StateStore.has_transitioned_through()` checks
  the AUDIT TRAIL (not just the current state value) for a genuine
  `AWAITING_APPROVAL → APPROVED` record.
- `orchestrator/uploader.py`'s `PolygonUploader` calls that check before
  **every single mutating method**, independent of whether you went through
  `Orchestrator` at all — so even a script that imports `PolygonUploader`
  directly and skips `Orchestrator` entirely still gets refused.
- None of this is airtight against a truly determined bypass (nothing
  running in the same process as an agent with full Python access can be) —
  but it is airtight against exactly the incident that already happened, and
  it will not silently look like success if you try something similar.

---

# Skill: reviewer-agent

> Runs only during BUILDING_PACKAGE. The only agent that reads Polygon's build-failure comment. Classifies the failure and routes a patch to the correct upstream agent. Authorized to trigger ESCALATE_TO_HUMAN.

# reviewer-agent

Input: the Polygon `buildPackage(verify=True)` failure — `state` (`FAILED` or
`TIMEOUT`) + the free-text `comment` from `problem.packages` (via
`orchestrator/pipeline.py::build_and_verify`, surfaced as a `BuildFailure`) —
plus `tutorials/invocations.md` and the expected roster behavior from
`PROBLEM_SPEC.md`. You do not edit artifacts — you classify and route.

Polygon has no invocations API (§9.4, confirmed live): there is no per-test
verdict matrix to read anymore, only this one comment. `buildPackage(
verify=True)` is still a real judge run of every solution against every
test with strict per-tag enforcement (live-verified: a full roster build
correctly flagged MA/OK/TL/WA mismatches by name) — the comment just reports
it at build granularity, not per-test. `orchestrator/reviewer.py`'s
`classify_build_failure` already runs a code-level check before you're
dispatched: if the comment implicates the `MA` solution or another
`OK`-tagged reference solution, it has already escalated in code (§1.5) and
you are not invoked. Your job is everything else — reading free text and
deciding which tab it points at.

## Expected tag behavior (§15)
| Solution tag | Expected on Polygon's build |
|---|---|
| `MA` | AC on every test (if this fails, code already escalated before you ran) |
| `OK` (correct.py / correct_alt.*) | AC on every test — same rule, code-enforced |
| `TL` (brute.\*, TLE1–TLEk) | TL on the adversarial/max tier; brute additionally AC on small/medium |
| `WA` / `RE` / `ML` / `RJ` | that verdict on ≥1 test, never AC on all |

## Failure → fix-target routing (§15)
| Comment mentions / implies | Classification | Route to |
|---|---|---|
| A validator rejecting a VALID-tagged test, or accepting an INVALID one | Validator bug | validator-agent |
| A checker rejecting a valid alternate output (custom checker only) | Checker bug | checker-agent (patch checker.cpp) |
| Compile error in a generator, or a script/test-index problem | Test-plan defect | generator-agent |
| A `TL`-tagged too-slow target (`TLE*`) that didn't actually TLE | Adversarial tier doesn't force the near-miss over — the core quality hole | generator-agent (build a stronger worst-case shape/size per §12.5's margin discipline; ≥5–10× over TL by construction, not a near-miss) |
| `brute.*` never hits TL, or TLEs on every tier | Tier sizing wrong | generator-agent (adjust small/medium/max tier sizes) |
| A `WA`/`RE`/`ML`/`RJ`-tagged solution came back AC on everything | Broken fixture, or the test set is too weak to expose the intended bug | solutions-agent (sharpen the bug) or generator-agent (add the input shape from the spec's named trap that should have caught it) |
| A `WA`/`RE`/`ML`/`RJ`-tagged solution produced a *different* violating verdict than its tag | Mislabeled fixture — really failing, but not for the claimed reason | solutions-agent (fix the bug or the tag until they agree) |
| Comment implicates `MA` or an `OK`-tagged solution | Spec ambiguity / checker bug / limits set too tight | **already escalated in code before you ran (§1.5) — you should not normally see this** |

Each routed patch is scoped to exactly one artifact and gets its own upload +
commit when `finish` is re-run (§11) — `upload()` is idempotent, so re-running
it after your routed patch never re-creates the problem or loses
already-good tabs. Report the comment verbatim in your classification so the
orchestrator's audit trail is complete. You may still trigger
`ESCALATE_TO_HUMAN` yourself if the comment is genuinely ambiguous between
routes, or when `retry_cap` is exhausted (code already halts on this — see
`orchestrator/pipeline.py::build_and_verify` — but say so plainly in your
report either way).
