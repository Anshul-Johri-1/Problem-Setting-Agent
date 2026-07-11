"""Runner wiring — how the pipeline dispatches real subagents (§8).

The `Orchestrator` takes a `runner(agent_name, payload) -> Any`. Its job is to
run the named subagent so it writes its artifacts into the problem dir. There are
three concrete shapes:

  * `CallbackRunner(dispatch_fn)` — the real one. `dispatch_fn(agent_name, prompt)`
    is supplied by whoever CAN invoke a subagent. In Claude Code that is the
    orchestrator agent calling the **Agent tool** with subagent_type=agent_name;
    in a headless host it wraps the Agent SDK / `claude -p`. This module builds
    the prompt (agent definition + its tutorial + the payload); the host performs
    the model call. This keeps Python free of any model dependency.

  * `ArtifactRunner()` — for hosts that dispatch subagents out-of-band (e.g. the
    assistant runs the subagent via the Agent tool, THEN drives the Python state
    machine). It validates that each agent's required artifacts now exist in the
    problem dir, so the state machine only advances on real output.

  * `FixtureRunner(fixture_dir)` — tests/demos with no model: copies a known-good
    problem's artifacts. Used by the test suite.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parent.parent
AGENTS = REPO / ".claude" / "agents"
TUTORIALS = REPO / "tutorials"

# Each subagent gets ONLY its own tutorial (§8, deliberately narrow context).
_TUTORIAL = {
    "spec-agent": "statement.md",
    "statement-agent": "statement.md",
    "validator-agent": "validator.md",
    "checker-agent": "checker.md",
    "solutions-agent": "solutions.md",
    "generator-agent": "generator.md",
    "reviewer-agent": "invocations.md",
}

# Artifacts each agent must produce (for ArtifactRunner validation).
_REQUIRED_ARTIFACTS = {
    "spec-agent": ["PROBLEM_SPEC.md"],
    "validator-agent": ["validator.cpp"],
    "generator-agent": ["script.txt"],
    "solutions-agent": ["solutions"],
    # statement/checker outputs vary (checker may be a standard choice, no file)
}


def _strip_frontmatter(md: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", md, re.DOTALL)
    return m.group(1).strip() if m else md.strip()


def build_agent_prompt(agent_name: str, payload: dict) -> str:
    """Compose the prompt for a subagent: its definition + its tutorial + the
    payload. This is exactly what a dispatch_fn should send to the subagent."""
    parts = []
    defn = AGENTS / f"{agent_name}.md"
    if defn.exists():
        parts.append(f"# Your role\n{_strip_frontmatter(defn.read_text())}")
    tut = _TUTORIAL.get(agent_name)
    if tut and (TUTORIALS / tut).exists():
        parts.append(f"# Reference tutorial ({tut})\n{(TUTORIALS / tut).read_text()}")
    import json
    parts.append(f"# Task payload\n```json\n{json.dumps(payload, indent=2)}\n```")
    if "spec_dir" in payload:
        parts.append(f"# Output location\nWrite your artifacts into: {payload['spec_dir']}")
    return "\n\n".join(parts)


class CallbackRunner:
    """Real runner. Delegates the model call to a host-provided dispatch_fn."""

    def __init__(self, dispatch_fn: Callable[[str, str], object]):
        self._dispatch = dispatch_fn

    def __call__(self, agent_name: str, payload: dict):
        return self._dispatch(agent_name, build_agent_prompt(agent_name, payload))


class ArtifactRunner:
    """For out-of-band dispatch: validates the subagent's artifacts exist."""

    def __init__(self, problem_dir: Path):
        self.problem_dir = Path(problem_dir)

    def __call__(self, agent_name: str, payload: dict):
        for rel in _REQUIRED_ARTIFACTS.get(agent_name, []):
            if not (self.problem_dir / rel).exists():
                raise FileNotFoundError(
                    f"{agent_name} was expected to produce '{rel}' in "
                    f"{self.problem_dir}, but it is missing.")
        return "validated"


class FixtureRunner:
    """Tests/demos with no model: copy a known-good problem's artifacts."""

    def __init__(self, problem_dir: Path, fixture_dir: Path):
        self.problem_dir = Path(problem_dir)
        self.fixture_dir = Path(fixture_dir)

    def __call__(self, agent_name: str, payload: dict):
        if agent_name == "spec-agent":
            (self.problem_dir / "PROBLEM_SPEC.md").write_text(
                f"# PROBLEM_SPEC: {self.problem_dir.name}\n(fixture)\n")
            return "spec-written"
        for item in ("meta.json", "validator.cpp", "script.txt"):
            if (self.fixture_dir / item).exists():
                shutil.copy(self.fixture_dir / item, self.problem_dir / item)
        for sub in ("generators", "solutions", "samples", "validator_stress", "validator_valid"):
            if (self.fixture_dir / sub).exists():
                shutil.copytree(self.fixture_dir / sub, self.problem_dir / sub,
                                dirs_exist_ok=True)
        return "artifacts-written"
