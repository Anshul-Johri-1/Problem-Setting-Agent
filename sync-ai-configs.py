#!/usr/bin/env python3
"""Generate all tool-specific AI configs from the single source of truth (§3).

`.claude/agents/*.md` is the ONLY place agent behavior is authored, and
`.claude/GUARDRAILS.md` is the ONLY place the "don't bypass the pipeline"
rules are authored. This script regenerates every other tool's format from
both. Run by the pre-commit hook, so generated files never drift. Never
hand-edit a generated file — it will be overwritten on the next commit.

GUARDRAILS.md is prepended to EVERY generated file, prominently, before any
agent-role content — this exists specifically so no AI tool driving this repo
(Claude, Gemini, Copilot, Codex, Windsurf, ...) can plausibly have missed it.
See GUARDRAILS.md itself for why this matters; short version: an agent once
bypassed every other guardrail in this repo by writing ad hoc scripts instead
of following the documented process, so the process is now also stated
directly, unmissably, in whatever context file each tool actually loads.

Targets:
  .cursor/rules/*.mdc            one rule file per agent (Cursor)
  .github/copilot-instructions.md   flattened single file (Copilot)
  AGENTS.md                      flat format (OpenAI Codex)
  GEMINI.md                      flat format (Gemini CLI / Gemini-based tools)
  .windsurfrules                 flat format (Windsurf)
  .agents/skills/*.md            skills format (Antigravity)
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
AGENTS_DIR = REPO / ".claude" / "agents"
COMMANDS_DIR = REPO / ".claude" / "commands"
GUARDRAILS_PATH = REPO / ".claude" / "GUARDRAILS.md"

GENERATED_BANNER = (
    "<!-- AUTO-GENERATED from .claude/agents/ + .claude/GUARDRAILS.md by "
    "sync-ai-configs.py. DO NOT EDIT — changes will be overwritten on the "
    "next commit. -->"
)


def load_guardrails() -> str:
    if not GUARDRAILS_PATH.exists():
        return ""
    return GUARDRAILS_PATH.read_text().strip()


def parse_agent(path: Path) -> dict:
    text = path.read_text()
    fm: dict[str, str] = {}
    body = text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
        body = m.group(2).strip()
    return {
        "slug": path.stem,
        "name": fm.get("name", path.stem),
        "description": fm.get("description", ""),
        "tools": fm.get("tools", ""),
        "body": body,
    }


def load_agents() -> list[dict]:
    return [parse_agent(p) for p in sorted(AGENTS_DIR.glob("*.md"))]


# --------------------------------------------------------------------------- #
def gen_cursor(agents: list[dict], guardrails: str) -> None:
    out = REPO / ".cursor" / "rules"
    out.mkdir(parents=True, exist_ok=True)
    for a in agents:
        (out / f"{a['slug']}.mdc").write_text(
            f"---\ndescription: {a['description']}\nglobs:\nalwaysApply: false\n---\n"
            f"{GENERATED_BANNER}\n\n{guardrails}\n\n---\n\n# {a['name']}\n\n{a['body']}\n"
        )


def gen_copilot(agents: list[dict], guardrails: str) -> None:
    out = REPO / ".github" / "copilot-instructions.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    parts = [GENERATED_BANNER, "", guardrails, "\n---\n",
             "\n# Polygon Problem Creation Agent — Copilot Instructions\n",
             "This repo defines a multi-agent pipeline. Each section is one "
             "agent's behavior; follow the one matching the task at hand.\n"]
    for a in agents:
        parts.append(f"\n## {a['name']}\n\n_{a['description']}_\n\n{a['body']}\n")
    out.write_text("\n".join(parts))


def gen_flat(agents: list[dict], guardrails: str, target: Path, title: str) -> None:
    parts = [GENERATED_BANNER, "", guardrails, "\n---\n", f"\n# {title}\n"]
    for a in agents:
        parts.append(f"\n## {a['name']}\n\n_{a['description']}_\n\n{a['body']}\n")
    target.write_text("\n".join(parts))


def gen_antigravity(agents: list[dict], guardrails: str) -> None:
    out = REPO / ".agents" / "skills"
    out.mkdir(parents=True, exist_ok=True)
    for a in agents:
        (out / f"{a['slug']}.md").write_text(
            f"{GENERATED_BANNER}\n\n{guardrails}\n\n---\n\n# Skill: {a['name']}\n\n"
            f"> {a['description']}\n\n{a['body']}\n"
        )


def main() -> int:
    agents = load_agents()
    guardrails = load_guardrails()
    if not agents:
        print("No agents found in .claude/agents/ — nothing to sync.")
        return 1
    if not guardrails:
        print("WARNING: .claude/GUARDRAILS.md missing or empty — syncing without it.")
    gen_cursor(agents, guardrails)
    gen_copilot(agents, guardrails)
    gen_flat(agents, guardrails, REPO / "AGENTS.md", "Agent Definitions (OpenAI Codex)")
    gen_flat(agents, guardrails, REPO / "GEMINI.md", "Agent Definitions (Gemini)")
    gen_flat(agents, guardrails, REPO / ".windsurfrules", "Agent Definitions (Windsurf)")
    gen_antigravity(agents, guardrails)
    print(f"Synced {len(agents)} agents + GUARDRAILS.md → "
         f"cursor, copilot, codex, gemini, windsurf, antigravity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
