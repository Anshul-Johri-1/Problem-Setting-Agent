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

2. **Never fabricate, hardcode, or skip the local self-check.** If you
   believe `local_harness` is slow, wrong, or unnecessary for a specific
   change, say so to the human and wait — do not invent a verdict matrix by
   hand and pass it downstream as if it were real. `orchestrator.cli
   local-check <name>` is fast, free, and safe to run as many times as you
   want; there's no situation where hand-writing a fake result instead is the
   right call.

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

# Skill: statement-agent

> Post-approval only. Writes statement.tex and tutorial.tex (editorial) from the approved spec in Newton house style — short, precise, no narrative flavor text.

# statement-agent

Input: the approved `PROBLEM_SPEC.md` + `tutorials/statement.md`. Output:
`problems/<name>/statement.tex` and `problems/<name>/tutorial.tex`.

## House style (tutorials/statement.md)
- **No narrative flavor text.** Get straight to the task. The Legend states the
  problem, not a story.
- **Pull "Indexing & Semantics" from `PROBLEM_SPEC.md` and state it
  explicitly** — 0- vs 1-indexed, inclusive/exclusive ranges, contiguity,
  empty-case handling, tie-breaking. This is required regardless of whether a
  sample happens to make it obvious; it's the most common real source of
  contest-time clarification threads, and terseness elsewhere doesn't excuse
  leaving this implicit.
- Input / Output sections are literal format specs — exact line counts, token
  order, ranges. If the spec states a sum-across-test-cases cap, include it.
- Notes explain a sample case only if genuinely non-obvious — this is
  separate from, and doesn't substitute for, the semantics requirement above.
- Legend rarely exceeds 4–5 sentences for a standard problem.
- Use Polygon `$...$` LaTeX for math; follow the Polygon statements manual.

## Sections
`Legend`, `Input`, `Output`, `Notes` (+ `Scoring` only if the spec defines
subtasks). Samples come from the test set, not hardcoded here.

The editorial (`tutorial.tex`) states the intended algorithm and complexity
from the spec — concise, no re-derivation of the story.
