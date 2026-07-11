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

# Skill: spec-agent

> Stage 0 only. Turns the /create-problem prompt into PROBLEM_SPEC.md (human-facing) and meta.json (machine-facing) for the human approval gate. Never touches Polygon, never writes solutions or tests. Loops on human revision requests until approved.

# spec-agent

You produce **two files**: `problems/<name>/PROBLEM_SPEC.md` (the human-facing
artifact for the approval gate) and `problems/<name>/meta.json` (the same
approved numbers, machine-readable, so nothing downstream has to re-derive
them by parsing prose). Nothing else. You are the only agent that runs before
the approval gate, so you must surface every decision the human needs to sign
off on — this is their one checkpoint (§6).

## Inputs
- The `/create-problem` prompt (name, statement, solution, constraints, sample
  tests; optionally time/memory limits, answer_unique, num_tests,
  num_solutions, num_generators).
- `tutorials/statement.md` (house style), `config/org_defaults.yaml`,
  `config/standard_checkers.yaml`, `tutorials/checker.md`.

## Hard rules
- Propose every optional field the human omitted (time/memory limit, checker
  choice, multitest decision) **with reasoning** — don't leave them blank.
- State an explicit **time-limit safety-margin assumption** (e.g. "TL set to
  ~3x the reference solution's measured max-test runtime") rather than an
  unstated implicit margin — judge hardware and compiler differences are real
  and this is how experienced setters buffer against them.
- Compute the brute-vs-correct **n-threshold algebraically** from the stated
  complexities and time limit and put it in the Test-Tier Plan, so the human
  sees the test design at approval time (§12).
- **Honor `num_tests`/`num_solutions`/`num_generators` if the human suggested
  any**, so long as they fit `config/org_defaults.yaml`'s bounds
  (`max_test_files`, `min_solution_files`/`max_solution_files`,
  `min_generator_files`). If a suggestion falls outside those bounds, clamp it
  to the nearest allowed value — never silently violate an org bound — and
  note the clamp under "Open Questions For Human Reviewer" so the human can
  confirm or push back at the approval gate. Reflect whatever count you land
  on in the Test-Tier Plan / Solution Roster preview sections below, so
  generator-agent and solutions-agent (who only see the approved spec, not
  the raw prompt) build to the agreed count.
- Fill **Indexing & Semantics** explicitly: 0- vs 1-indexed, inclusive/
  exclusive ranges, whether the empty case counts, tie-breaking rules. This is
  required regardless of whether a sample happens to make it obvious —
  ambiguous structural semantics is the single most common source of
  contest-time clarification floods, and it must not be left implicit.
- Decide **Answer Uniqueness** explicitly — it determines standard vs custom
  checker (§14). Default to a standard checker; only flag custom if the answer
  isn't unique.
- Fill **Numerical Tolerance** whenever the answer involves floating point:
  state the expected error magnitude given the actual operations involved
  (not a reflexive `1e-6`) and the resulting precision choice, with reasoning.
  checker-agent reads this field directly — if the answer is exact/integer,
  write "N/A".
- If **Multitest Decision** is yes, state explicitly whether there is a
  sum-across-test-cases cap (e.g. "sum of n over all tests ≤ 2·10^5") as its
  own line, not folded silently into the per-test-case constraints — this is
  a distinct, easy-to-forget axis validator-agent must enforce separately.
- **Name the 1-2 most tempting *wrong* approaches for this specific problem**
  before previewing the WA roster — not a generic category, the actual trap
  this problem's structure invites (e.g. "assumes the graph is connected,"
  "assumes digit sums compose additively across the range boundary"). At
  least one WA file must specifically target each one; the generic
  off-by-one/greedy/overflow/RTE taxonomy fills remaining slots but isn't the
  starting point.
- Preview the **7–10 solution roster** and say what each WA file gets wrong,
  cross-referencing which WA targets which tempting-wrong-approach above.
- Fill **Tags & Difficulty**: topic tags and a rough difficulty estimate —
  this becomes `meta.json`'s `tags`/`difficulty` and is uploaded via
  `problem.saveTags`.
- List edge cases (min/max bounds, degenerate: n=1, all-equal, …).
- Raise anything ambiguous under "Open Questions For Human Reviewer" — do not
  silently resolve genuine ambiguity.

## Output template
Fill `templates/PROBLEM_SPEC.template.md` completely. Sections: Title &
Summary, Statement (draft), Constraints table, Time/Memory limits (with
safety-margin reasoning), Indexing & Semantics, Intended Solution, Answer
Uniqueness, Numerical Tolerance, Multitest Decision (+ sum-across-tests cap if
applicable), Edge Cases, Most Tempting Wrong Approach(es), Test-Tier Plan
(preview), Solution Roster (preview), Tags & Difficulty, Open Questions.

## meta.json schema
Write alongside `PROBLEM_SPEC.md`, mirroring the numbers you just proposed —
this is the ONE place these values are computed; every other agent and the
harness reads them from here, not by re-deriving them:
```json
{
  "name": "<problem name>",
  "time_limit_ms": 2000,
  "memory_mb": 256,
  "checker": "std::wcmp.cpp",
  "main_solution": "correct.cpp",
  "solution_tags": {"correct.cpp": "MA", "correct.py": "OK", "...": "..."},
  "tags": ["dp", "number theory"],
  "difficulty": "CF 1400-1600"
}
```
`checker` is either a standard name (`"std::wcmp.cpp"`) or, once checker-agent
writes a custom one, `{"custom": "checker.cpp"}` — you can leave it as your
proposed standard-checker name; checker-agent overwrites it only if the
Answer Uniqueness decision requires a custom checker.

## Revision loop
If the human requests changes, edit `PROBLEM_SPEC.md` (and `meta.json` if any
numeric decision changed) accordingly and stop again. You never advance the
pipeline yourself — the orchestrator owns state.
