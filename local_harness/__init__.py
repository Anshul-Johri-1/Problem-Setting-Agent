"""Local self-check harness (§10) — runs after generation, before any upload.

All local compute, no API calls, fast iteration. Only a fully green run lets the
orchestrator leave LOCAL_SELF_CHECK. `run_all` orchestrates: compile →
materialize → validator_stress → cross_check → tle_probe → sanitize_check →
spec_consistency → judge → roster check (incl. EXPECTED_VERDICT + coverage
overlap) → stress phase (differential WA search + too-slow-target worst-case
sweep, §10.5).

Backs `polygon_client.invocations.LocalHarnessInvocations` (the confirmed answer
to the §9.4 invocations-API gap).
"""

from .problem import Problem
from .run import run_all, HarnessReport
from .compile import compile_all
from .cross_check import cross_check
from .tle_probe import tle_probe
from .validator_stress import validator_stress
from .sanitize_check import sanitize_check
from .spec_consistency import spec_consistency
from .judge import judge
from .stress import stress_correctness, tle_search

__all__ = [
    "Problem", "run_all", "HarnessReport",
    "compile_all", "cross_check", "tle_probe", "validator_stress",
    "sanitize_check", "spec_consistency", "judge",
    "stress_correctness", "tle_search",
]
