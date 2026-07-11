"""Access-granting stub (§9.5 — CONFIRMED GAP).

FINDING (2026-07-11): Granting a user access to a problem is a UI-only action
("Add users" on the problem page). It is NOT exposed via the Polygon API. This
is confirmed by:
  * The Polygon team's own historical statement that access is UI-only.
  * Its absence from every method list found, including polyman's 50+ methods.
    (polyman only READS access: `problem.info` returns an `accessType` field of
    READ/WRITE/OWNER; there is no set/grant counterpart.)

Per the decision log (§0), this is deliberately NOT automated via browser
automation — it is the one manual step left for the human, IF the org config
requires one. This module is a no-op that returns the reminder string
surfaced in the final output (§17).
"""

from __future__ import annotations

# Org-wide required grants (mirrors config/org_defaults.yaml → access_grants).
# Empty by default — no collaborator is auto-required. Populate this (or read
# it from config/org_defaults.yaml) if your org wants every new problem to get
# a standing reminder to add a specific collaborator.
REQUIRED_GRANTS: list[dict[str, str]] = []


def access_reminder(owner_handle: str, problem_name: str,
                    grants: list[dict[str, str]] | None = None) -> str:
    """Return the manual-access reminder, or "" if no grants are required."""
    grants = REQUIRED_GRANTS if grants is None else grants
    if not grants:
        return ""
    grant_list = ", ".join(f"`{g['handle']}` ({g['permission']})" for g in grants)
    return (
        f"⚠️  One manual step left: on the Polygon problem page for "
        f"'{problem_name}' (owner: {owner_handle}), open the 'Manage access' / "
        f"'Add users' tab and grant {grant_list}. Polygon does not expose access "
        f"grants via API, so this cannot be automated."
    )
