# Polygon Problem Creation Agent

Agentic pipeline that turns one structured prompt into a fully tested, committed,
packaged Codeforces **Polygon** problem — with exactly one human approval gate,
then autonomous through to a working Polygon link.

Built on the architecture of
[7oSkaaa/polygon-problems-generator](https://github.com/7oSkaaa/polygon-problems-generator),
adapted for our org. See [`guidelines.md`](guidelines.md) for the full workflow
and the build spec for the complete design.

## Quick start (per person, per fork)

```bash
git clone <this-repo> && cd polygon-problem-agent
cp .env.example .env            # fill in YOUR Polygon API key/secret; never commit
git config core.hooksPath .githooks   # keep tool configs auto-synced
python3 tests/test_gate.py      # sanity-check the approval gate + state machine
```

Then, in your AI tool of choice, run `/create-problem` with the input contract
in [`.claude/commands/create-problem.md`](.claude/commands/create-problem.md).

## How it works

1. **spec-agent** drafts `PROBLEM_SPEC.md` and the pipeline **stops** at the one
   hard approval gate. The gate is enforced in **code**
   ([`orchestrator/gate.py`](orchestrator/gate.py)) — no generation, file write,
   or Polygon call can happen before you approve.
2. On approval, the **orchestrator** runs generation → tab-by-tab upload +
   commit → Polygon's own `buildPackage(verify=True)` → sample-output
   verification → finalize, autonomously — through
   [`orchestrator/cli.py`](orchestrator/cli.py), the single sanctioned
   entrypoint for anything that touches live Polygon (see Guardrails below).
   Nothing compiles or runs any solution/generator/validator/checker
   locally, anywhere — Polygon's build is the one verification gate, which is
   what keeps this fast and cheap.
3. You get a Polygon link. If your org config (`config/org_defaults.yaml` →
   `access_grants`) lists any required collaborators, you'll also get a manual
   reminder to add them (Polygon has no API for granting access) — empty by
   default, so most runs skip this entirely.

## Guardrails — read if you're pointing a different AI tool at this repo

**[`.claude/GUARDRAILS.md`](.claude/GUARDRAILS.md)** is the full account of
why this matters and is synced into every tool's own config format (Cursor,
Copilot, Codex, Gemini, Windsurf, Antigravity) so it's visible no matter which
AI is driving the repo. Short version: an agent once bypassed the entire
pipeline — forged approval, fabricated the local self-check, uploaded
unverified content to two real Polygon problems — by writing ad hoc Python
against the internals instead of following the documented process. The fix
isn't just better docs (an agent with code-execution access can always ignore
a markdown file): `orchestrator/uploader.py`'s `PolygonUploader` now
independently re-verifies a genuine, audit-trail-backed approval before
**every** live call, regardless of how it's constructed or called — see
`tests/test_cli.py` for the reproduction and fix.

## Credentials & the fork model

Each fork is one person's local copy. Only `.env` differs (gitignored). The
shared repo — agents, tutorials, tool schemas, config — stays byte-identical
across forks. Credentials are read directly by the tool layer from the
environment and **never enter agent/LLM context**.

## Layout

| Path | What |
|---|---|
| `.claude/agents/` | **Source of truth** for all agent behavior |
| `.claude/commands/create-problem.md` | the `/create-problem` entry point |
| `orchestrator/` | state machine + the structural approval gate (§6, §7) + the build-and-verify gate (§15) |
| `polygon_client/` | Polygon API tool layer — signing + methods (live-verified) |
| `templates/`, `tutorials/` | base files + house-style guides read at runtime |
| `config/` | `org_defaults.yaml`, `standard_checkers.yaml` (live-verified names) |
| `orchestrator/cli.py` | **the single sanctioned entrypoint** for anything live (§ Guardrails) |
| `.claude/GUARDRAILS.md` | why ad hoc scripts against internals are forbidden, synced everywhere |
| `sync-ai-configs.py` | regenerates Cursor/Copilot/Codex/Gemini/Windsurf/Antigravity |
| `docs/POLYGON_API_FINDINGS.md` | live §18 verification results |
| `scripts/inspect_problem.py` | read-only problem inspection — use this to debug, never a new script |

## API layer note

The Polygon client is **hand-rolled in Python** (signing recipe verified live).
[polyman](https://hamzahassanain.github.io/polyman/) (MIT, TypeScript) is a
capable alternative SDK if you'd rather not maintain the signing layer — but it
adds a Node runtime alongside this Python codebase.

## Known Polygon API gaps (verified live 2026-07-11)

- **Invocations** (running solutions / reading a per-test verdict): not
  API-exposed → the pipeline relies entirely on `buildPackage(verify=True)`'s
  terminal state + free-text comment instead (`orchestrator/pipeline.py::
  build_and_verify`, classified in `orchestrator/reviewer.py`). There is no
  local fallback — nothing in this pipeline compiles or runs any
  solution/generator/validator/checker locally.
- **Access-granting**: not API-exposed → the one deliberate manual step
  (`polygon_client/access.py` prints the reminder).

Full detail: [`docs/POLYGON_API_FINDINGS.md`](docs/POLYGON_API_FINDINGS.md).
