"""Parse the /create-problem input block (§5).

Fields are `key: value` lines; values may continue onto indented following
lines. `sample tests:` introduces an Input/Output block. Required fields:
name, statement, solution, constraints, sample tests. Optional: time_limit,
memory_limit, answer_unique.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REQUIRED = ("name", "statement", "solution", "constraints")
KNOWN_KEYS = {"name", "statement", "solution", "constraints",
              "time_limit", "memory_limit", "answer_unique"}

_NAME_RE = re.compile(r"^[a-z0-9-]+$")


class InputError(ValueError):
    pass


@dataclass
class SampleTest:
    input: str
    output: str


@dataclass
class CreateProblemInput:
    name: str
    statement: str
    solution: str
    constraints: str
    samples: list[SampleTest] = field(default_factory=list)
    time_limit: str | None = None
    memory_limit: str | None = None
    answer_unique: str | None = None

    def validate(self) -> None:
        for f in REQUIRED:
            if not getattr(self, f, "").strip():
                raise InputError(f"missing required field: {f}")
        if not self.samples:
            raise InputError("missing required field: sample tests")
        if not _NAME_RE.match(self.name):
            raise InputError(
                f"name '{self.name}' must match [a-z0-9-]+ (Polygon rule; no underscores)")


def _clean_chunk(chunk: str) -> str:
    """Strip each line's alignment indentation (safe: leading whitespace is not
    significant in CP token streams) and drop leading/trailing blank lines."""
    lines = [ln.strip() for ln in chunk.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _parse_samples(block: list[str]) -> list[SampleTest]:
    """Parse an Input:/Output: sample block (may have multiple pairs)."""
    text = "\n".join(block)
    # Split into Input:/Output: segments preserving order.
    parts = re.split(r"(?im)^\s*(input|output)\s*:", text)
    # parts = ['', 'Input', '<in>', 'Output', '<out>', 'Input', ...]
    samples: list[SampleTest] = []
    cur_in = None
    i = 1
    while i < len(parts) - 1:
        label = parts[i].strip().lower()
        chunk = _clean_chunk(parts[i + 1])
        if label == "input":
            cur_in = chunk
        elif label == "output":
            samples.append(SampleTest(input=(cur_in or "") + "\n", output=chunk + "\n"))
            cur_in = None
        i += 2
    return samples


def parse_create_problem(text: str) -> CreateProblemInput:
    lines = text.splitlines()
    # drop a leading "/create-problem" line if present
    if lines and lines[0].strip().startswith("/create-problem"):
        lines = lines[1:]

    fields: dict[str, str] = {}
    sample_block: list[str] = []
    cur_key: str | None = None
    in_samples = False

    for line in lines:
        low = line.strip().lower()
        if low.startswith("sample tests:") or low.startswith("sample test:"):
            in_samples = True
            cur_key = None
            continue
        if in_samples:
            sample_block.append(line)
            continue
        m = re.match(r"^([a-z_ ]+):\s*(.*)$", line)
        key = m.group(1).strip().replace(" ", "_").lower() if m else None
        if key in KNOWN_KEYS:
            cur_key = key
            fields[cur_key] = m.group(2).strip()  # type: ignore
        elif cur_key and line.strip():  # continuation line
            fields[cur_key] += ("\n" + line.strip())

    inp = CreateProblemInput(
        name=fields.get("name", ""),
        statement=fields.get("statement", ""),
        solution=fields.get("solution", ""),
        constraints=fields.get("constraints", ""),
        samples=_parse_samples(sample_block),
        time_limit=fields.get("time_limit"),
        memory_limit=fields.get("memory_limit"),
        answer_unique=fields.get("answer_unique"),
    )
    inp.validate()
    return inp
