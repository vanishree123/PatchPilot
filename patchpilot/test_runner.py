"""Run only the approved fixed pytest command in a controlled demo copy."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .workspace import WORKSPACE_ROOT


@dataclass(frozen=True)
class RunResult:
    status: str
    return_code: int | None
    stdout: str
    stderr: str


def fixed_test_argv() -> list[str]:
    return [sys.executable, "-m", "pytest", "tests/test_discount.py", "-q"]


def _child_environment() -> dict[str, str]:
    child_env = os.environ.copy()
    child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    child_env.pop("PYTEST_PLUGINS", None)
    child_env.pop("PYTEST_ADDOPTS", None)
    return child_env


def run_targeted_test(workspace: Path, timeout_seconds: int = 10) -> RunResult:
    workspace_path = workspace.resolve(strict=True)
    root = WORKSPACE_ROOT.resolve()
    if not workspace_path.is_relative_to(root):
        raise ValueError("Test workspace is outside runtime/demo_workspaces")
    try:
        completed = subprocess.run(
            fixed_test_argv(),
            cwd=workspace_path,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=_child_environment(),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return RunResult("timed_out", None, stdout, stderr)
    status = "passed" if completed.returncode == 0 else "failed"
    return RunResult(status, completed.returncode, completed.stdout, completed.stderr)
