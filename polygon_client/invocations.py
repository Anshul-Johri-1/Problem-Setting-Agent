"""Invocations abstraction (§9.4 — FLAGGED GAP).

FINDING (2026-07-11): The Polygon API does NOT expose a method to trigger an
Invocations run (running solutions against the testset on Polygon's judge) or to
read back the verdict matrix. This was confirmed by:
  * No such method in the confirmed method list (§9.1).
  * polyman — a mature 50+ method SDK — has no invoke/verdict/run-solution API
    call. Its own testing is done LOCALLY via an execa-based executor; its
    `VerdictTracker`/`CheckerVerdict` types describe local runs, not judge runs.

Per §9.4 the orchestrator must not depend on the mechanism. This module defines
a single abstract interface; the concrete backend is selected at runtime so §7
and §15 logic never changes.

Backends:
  * LocalHarnessInvocations  — default. Uses local_harness/ (§10) as the
    correctness gate. Weaker (misses Polygon-side compiler/timing differences)
    but zero external dependency. This mirrors what polyman does.
  * BrowserInvocations       — TODO. Drives the Polygon web UI to trigger
    Invocations and scrape the verdict page. Same fallback pattern the spec
    reserves for the access-grant step. Left unimplemented until/unless local
    verification proves insufficient in practice.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class VerdictMatrix:
    """Normalized invocation result the reviewer-agent (§15) consumes."""
    # {solution_filename: {test_index: verdict}}, verdict ∈ {AC, WA, TL, RE, ML, PE}
    results: dict[str, dict[int, str]] = field(default_factory=dict)
    # free-form notes / raw backend payload for the audit trail
    raw: str = ""

    def verdicts_for(self, solution: str) -> dict[int, str]:
        return self.results.get(solution, {})


class InvocationsBackend(Protocol):
    def run(self, problem_id: int) -> str: ...
    def results(self, problem_id: int, run_id: str) -> VerdictMatrix: ...


class BaseInvocations(abc.ABC):
    @abc.abstractmethod
    def run(self, problem_id: int) -> str:
        """Trigger a run; return an opaque run_id."""

    @abc.abstractmethod
    def results(self, problem_id: int, run_id: str) -> VerdictMatrix:
        """Poll/return the verdict matrix for a run."""


class LocalHarnessInvocations(BaseInvocations):
    """Default backend — delegates to local_harness/ (§10).

    Backed by `local_harness/`. Construct with the local problem scratch
    directory (problems/<name>/); `run` executes the harness judge there and
    caches the verdict matrix, `results` returns it. `problem_id` is accepted
    for interface parity but the local directory is the source of truth.
    """

    def __init__(self, problem_dir):
        from pathlib import Path
        self.problem_dir = Path(problem_dir)
        self._cache: dict[str, VerdictMatrix] = {}

    def run(self, problem_id: int) -> str:
        from local_harness.run import run_all
        report = run_all(self.problem_dir)
        run_id = f"local:{self.problem_dir.name}:{problem_id}"
        self._cache[run_id] = VerdictMatrix(results=report.matrix, raw=report.text())
        return run_id

    def results(self, problem_id: int, run_id: str) -> VerdictMatrix:
        if run_id not in self._cache:
            raise KeyError(f"no cached run {run_id!r}; call run() first")
        return self._cache[run_id]


def get_backend(name: str = "local", **kwargs) -> BaseInvocations:
    if name == "local":
        return LocalHarnessInvocations(problem_dir=kwargs["problem_dir"])
    raise ValueError(f"unknown invocations backend: {name!r} (browser backend not yet built)")
