#!/usr/bin/env python3
"""Generate all tool-specific AI configs from the single source of truth (§3).

`.claude/agents/*.md` is the ONLY place agent behavior is authored. This script
regenerates every other tool's format from it. Run by the pre-commit hook, so
generated files never drift. Never hand-edit a generated file — it will be
overwritten on the next commit.

Targets:
  .cursor/rules/*.mdc            one rule file per agent (Cursor)
  .github/copilot-instructions.md   flattened single file (Copilot)
  AGENTS.md                      flat format (OpenAI Codex)
  .windsurfrules                 flat format (Windsurf)
  .agents/skills/*.md            skills format (Antigravity)
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
AGENTS_DIR = REPO / ".claude" / "agents"
COMMANDS_DIR = REPO / ".claude" / "commands"

GENERATED_BANNER = (
    "<!-- AUTO-GENERATED from .claude/agents/ by sync-ai-configs.py. "
    "DO NOT EDIT — changes will be overwritten on the next commit. -->"
)


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
def gen_cursor(agents: list[dict]) -> None:
    out = REPO / ".cursor" / "rules"
    out.mkdir(parents=True, exist_ok=True)
    for a in agents:
        (out / f"{a['slug']}.mdc").write_text(
            f"---\ndescription: {a['description']}\nglobs:\nalwaysApply: false\n---\n"
            f"{GENERATED_BANNER}\n\n# {a['name']}\n\n{a['body']}\n"
        )


def gen_copilot(agents: list[dict]) -> None:
    out = REPO / ".github" / "copilot-instructions.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    parts = [GENERATED_BANNER,
             "\n# Polygon Problem Creation Agent — Copilot Instructions\n",
             "This repo defines a multi-agent pipeline. Each section is one "
             "agent's behavior; follow the one matching the task at hand.\n"]
    for a in agents:
        parts.append(f"\n## {a['name']}\n\n_{a['description']}_\n\n{a['body']}\n")
    out.write_text("\n".join(parts))


def gen_flat(agents: list[dict], target: Path, title: str) -> None:
    parts = [GENERATED_BANNER, f"\n# {title}\n"]
    for a in agents:
        parts.append(f"\n## {a['name']}\n\n_{a['description']}_\n\n{a['body']}\n")
    target.write_text("\n".join(parts))


def gen_antigravity(agents: list[dict]) -> None:
    out = REPO / ".agents" / "skills"
    out.mkdir(parents=True, exist_ok=True)
    for a in agents:
        (out / f"{a['slug']}.md").write_text(
            f"{GENERATED_BANNER}\n\n# Skill: {a['name']}\n\n"
            f"> {a['description']}\n\n{a['body']}\n"
        )


def main() -> int:
    agents = load_agents()
    if not agents:
        print("No agents found in .claude/agents/ — nothing to sync.")
        return 1
    gen_cursor(agents)
    gen_copilot(agents)
    gen_flat(agents, REPO / "AGENTS.md", "Agent Definitions (OpenAI Codex)")
    gen_flat(agents, REPO / ".windsurfrules", "Agent Definitions (Windsurf)")
    gen_antigravity(agents)
    print(f"Synced {len(agents)} agents → cursor, copilot, codex, windsurf, antigravity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
