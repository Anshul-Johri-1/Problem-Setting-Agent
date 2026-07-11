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
2. On approval, the **orchestrator** runs generation → local self-check →
   tab-by-tab upload + commit → invocation loop → package build, autonomously.
3. You get a Polygon link + one manual step: grant `newton_school` WRITE access
   (Polygon has no API for this).

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
| `orchestrator/` | state machine + the structural approval gate (§6, §7) |
| `polygon_client/` | Polygon API tool layer — signing + methods (live-verified) |
| `local_harness/` | local compile / cross-check / TLE / validator stress (§10) |
| `templates/`, `tutorials/` | base files + house-style guides read at runtime |
| `config/` | `org_defaults.yaml`, `standard_checkers.yaml` (live-verified names) |
| `sync-ai-configs.py` | regenerates Cursor/Copilot/Codex/Windsurf/Antigravity |
| `docs/POLYGON_API_FINDINGS.md` | live §18 verification results |
| `scripts/` | `verify_live.py`, `e2e_dry_run.py` |

## API layer note

The Polygon client is **hand-rolled in Python** (signing recipe verified live).
[polyman](https://hamzahassanain.github.io/polyman/) (MIT, TypeScript) is a
capable alternative SDK if you'd rather not maintain the signing layer — but it
adds a Node runtime alongside this Python codebase.

## Known Polygon API gaps (verified live 2026-07-11)

- **Invocations** (running solutions / reading verdicts): not API-exposed →
  handled via the abstracted `polygon_client/invocations.py` (local-harness
  backend by default).
- **Access-granting**: not API-exposed → the one deliberate manual step
  (`polygon_client/access.py` prints the reminder).

Full detail: [`docs/POLYGON_API_FINDINGS.md`](docs/POLYGON_API_FINDINGS.md).
