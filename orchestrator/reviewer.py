"""Build-failure classification (§15) — code-level safety net.

Polygon's API has no invocations endpoint (§9.4, confirmed live — see
docs/POLYGON_API_FINDINGS.md): there is no way to fetch a per-test verdict
matrix. The only diagnostic on a failed build is `problem.packages[].comment`,
a free-text string. That comment IS a real signal, though: `buildPackage(
verify=True)` strictly enforces every solution's declared tag against its
actual behavior on Polygon's own judge (live-verified: a full roster build
correctly flagged MA/OK/TL/WA mismatches), so a FAILED build with a comment
naming a solution or tab is Polygon itself reporting a real defect — just at
build granularity, not per-test.

Classifying which tab to patch from free text genuinely needs judgment now
(no more matrix to pattern-match), so that routing is reviewer-agent's job
(an LLM call — see `.claude/agents/reviewer-agent.md` and
`tutorials/invocations.md`'s routing table). This module keeps only the one
rule that must never be left to judgment: a failure implicating the MA
solution or another reference (`OK`-tagged) solution halts and escalates,
never auto-patched (§1.5) — the same hard rule the old matrix-based
`classify()` enforced with `low.startswith("correct")`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BuildResult:
    """Normalized result of `Uploader.build_package()` (state, comment)."""
    state: str  # READY | FAILED | TIMEOUT
    comment: str = ""


@dataclass
class Classification:
    clean: bool
    escalate: bool = False
    escalate_reason: str = ""
    notes: list[str] = field(default_factory=list)


def classify_build_failure(result: BuildResult, main_solution: str,
                           reference_solutions: list[str] | None = None
                           ) -> Classification:
    """Code-enforced short-circuit (§1.5).

    `main_solution` + `reference_solutions` (other OK-tagged correct
    solutions) are checked by substring against the comment. This is
    deliberately conservative — a false-negative (missing an implication of
    the MA solution) just means reviewer-agent handles routing as usual and a
    human still reviews any escalation reviewer-agent itself raises; a
    false-positive only causes an extra, harmless escalation. Silently
    auto-patching a real MA/OK failure is the one outcome this must prevent.
    """
    if result.state == "READY":
        return Classification(clean=True)

    comment_low = result.comment.lower()
    for name in filter(None, {main_solution, *(reference_solutions or [])}):
        if name.lower() in comment_low:
            return Classification(
                clean=False, escalate=True,
                escalate_reason=(
                    f"Polygon build {result.state} implicating reference "
                    f"solution '{name}': {result.comment or '(no comment)'}. "
                    f"Halting per §1.5 — a correct/reference solution failure "
                    f"is never auto-patched."))
    return Classification(clean=False, notes=[result.comment or f"build {result.state}, no comment"])
