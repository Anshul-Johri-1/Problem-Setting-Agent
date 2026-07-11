"""Shared build + run helpers for the local harness (§10).

All compilation goes through `compile_cpp` so the testlib include path and the
`-Wall -Wextra` policy are defined in exactly one place. All process execution
goes through `run` so timing/timeout/capture are uniform.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

VENDOR = Path(__file__).resolve().parent / "vendor"
TESTLIB_INCLUDE = str(VENDOR)

CXX = "g++"
CXX_FLAGS = ["-std=c++17", "-O2", "-I", TESTLIB_INCLUDE]
WARN_FLAGS = ["-Wall", "-Wextra"]


@dataclass
class CompileResult:
    ok: bool
    binary: Path | None
    stderr: str
    had_warnings: bool


def compile_cpp(src: Path, out: Path, *, warnings_as_errors: bool = True) -> CompileResult:
    """Compile one C++ file. With warnings_as_errors, any -Wall/-Wextra warning
    fails the build (§10 zero-tolerance)."""
    flags = list(CXX_FLAGS) + list(WARN_FLAGS)
    if warnings_as_errors:
        flags.append("-Werror")
    proc = subprocess.run(
        [CXX, *flags, "-o", str(out), str(src)],
        capture_output=True, text=True,
    )
    had_warnings = "warning:" in proc.stderr
    ok = proc.returncode == 0
    return CompileResult(ok=ok, binary=out if ok else None,
                         stderr=proc.stderr, had_warnings=had_warnings)


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    wall_ms: float
    timed_out: bool


def warmup(cmd: list[str]) -> None:
    """Pay one-time first-exec cost outside any timed measurement.

    macOS verifies a freshly-compiled binary on its FIRST execution (Gatekeeper),
    adding 100–300ms that would otherwise corrupt timing-based verdicts. Run the
    binary once with empty stdin (our programs hit EOF and exit immediately) and
    discard the result.
    """
    try:
        subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    except Exception:
        pass  # warmup is best-effort; never fail the harness on it


def run(cmd: list[str], *, stdin_path: Path | None = None,
        timeout_ms: int | None = None) -> RunResult:
    """Run a command, feeding stdin_path if given, with a wall-clock timeout.
    With no stdin_path, stdin is /dev/null (never inherit the parent's, which
    could hang a solution that reads stdin)."""
    stdin_f = stdin_path.open("rb") if stdin_path else subprocess.DEVNULL
    start = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd, stdin=stdin_f, capture_output=True,
            timeout=(timeout_ms / 1000.0) if timeout_ms else None,
        )
        exit_code = proc.returncode
        out, err = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        timed_out = True
        exit_code = -1
        out, err = e.stdout or b"", e.stderr or b""
    finally:
        if stdin_path is not None:
            stdin_f.close()
    wall_ms = (time.perf_counter() - start) * 1000.0
    return RunResult(
        exit_code=exit_code,
        stdout=out.decode("utf-8", "replace") if isinstance(out, bytes) else (out or ""),
        stderr=err.decode("utf-8", "replace") if isinstance(err, bytes) else (err or ""),
        wall_ms=wall_ms, timed_out=timed_out,
    )


def solution_cmd(path: Path, binary_dir: Path) -> tuple[list[str], Path | None]:
    """Return the run command for a solution file, plus a cpp source to compile.

    .py  → ['python3', file]  (no compile step)
    .cpp → [binary]           (caller must compile first)
    """
    if path.suffix == ".py":
        return (["python3", str(path)], None)
    if path.suffix == ".cpp":
        binary = binary_dir / path.stem
        return ([str(binary)], path)
    raise ValueError(f"unsupported solution type: {path.name}")
