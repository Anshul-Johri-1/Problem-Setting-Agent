"""Verdict-matrix classification (§15) — the reviewer-agent's logic in code.

Given a verdict matrix, decide: clean / patch-a-tab / escalate. The single most
important rule (§1.5): a CORRECT solution failing anywhere is an immediate
escalation, never an auto-patch.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Classification:
    clean: bool
    escalate: bool = False
    escalate_reason: str = ""
    # (fix_target_agent, human-readable issue) for non-escalating patches
    patches: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def classify(matrix: dict[str, dict[int, str]]) -> Classification:
    c = Classification(clean=True)

    for sol, row in matrix.items():
        verdicts = set(row.values())
        low = sol.lower()

        if low.startswith("correct"):
            if verdicts != {"AC"}:
                bad = {i: v for i, v in row.items() if v != "AC"}
                c.clean = False
                c.escalate = True
                c.escalate_reason = (
                    f"correct solution {sol} failed {bad} — likely spec ambiguity "
                    f"or checker bug. Halting per §1.5 (never auto-patched).")
                return c  # escalation short-circuits everything

        elif low.startswith("brute"):
            if "TL" not in verdicts:
                c.clean = False
                c.patches.append(("generator-agent",
                                  f"{sol} never TLEs — max tier too weak (§12)."))
            elif "AC" not in verdicts:
                c.clean = False
                c.patches.append(("generator-agent",
                                  f"{sol} TLEs everywhere — small/medium tiers too big (§12)."))
            else:
                c.notes.append(f"{sol}: partial-TLE pattern OK.")

        elif low.startswith("tle"):
            # Near-miss too-slow target (§12.5): a correct algorithm with a
            # fatal inefficiency. It MUST be forced over the limit by the
            # adversarial tier; if it slips through, the test set — not the
            # solution — is at fault, so route to generator-agent for a
            # stronger worst-case (this is the exact "queue-instead-of-heap
            # Dijkstra gets AC" hole the pipeline exists to close).
            if "TL" not in verdicts:
                c.clean = False
                c.patches.append(("generator-agent",
                                  f"{sol} (too-slow target) is never forced over the "
                                  f"limit — adversarial tier too weak (§12.5)."))
            elif "AC" not in verdicts:
                c.notes.append(f"{sol}: TL everywhere — models a brute, not a near-miss; "
                               f"consider a small tier it passes.")
            else:
                c.notes.append(f"{sol}: AC small / TL max as expected.")

        elif low.startswith("wa") or low.startswith("re"):
            if verdicts == {"AC"}:
                c.clean = False
                c.patches.append(("solutions-agent",
                                  f"{sol} is AC on all tests — broken fixture (§15)."))
            else:
                c.notes.append(f"{sol}: non-AC on ≥1 as expected.")

    return c
