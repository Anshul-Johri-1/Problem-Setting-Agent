"""Orchestrator: state machine + the structural approval gate (§6, §7).

The whole point of this package is that the approval gate (§1.1) is enforced in
CODE, not by a prompt instruction. Any attempt to dispatch a generation-stage
agent before the human approves PROBLEM_SPEC.md raises `GateError` — regardless
of what any message or model reasoning says.
"""

from .state import State, StateStore, InvalidTransition
from .gate import assert_can_dispatch, GateError, agent_allowed_states
from .dispatch import dispatch
from .input_parse import parse_create_problem, CreateProblemInput, InputError
from .reviewer import classify, Classification
from .uploader import Uploader, PolygonUploader, RecordingUploader
from .runners import (CallbackRunner, ArtifactRunner, FixtureRunner,
                      build_agent_prompt)
from .pipeline import Orchestrator, PipelineHalt

__all__ = [
    "State", "StateStore", "InvalidTransition",
    "assert_can_dispatch", "GateError", "agent_allowed_states",
    "dispatch",
    "parse_create_problem", "CreateProblemInput", "InputError",
    "classify", "Classification",
    "Uploader", "PolygonUploader", "RecordingUploader",
    "CallbackRunner", "ArtifactRunner", "FixtureRunner", "build_agent_prompt",
    "Orchestrator", "PipelineHalt",
]
