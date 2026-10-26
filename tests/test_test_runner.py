import subprocess
from types import SimpleNamespace

import pytest

from patchpilot.test_runner import fixed_test_argv, run_targeted_test
from patchpilot.workspace import create_fresh_workspace


def test_runner_uses_fixed_argv_shell_false_and_plugin_control(monkeypatch):
    workspace = create_fresh_workspace()
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="1 passed", stderr="")

    monkeypatch.setenv("PYTEST_PLUGINS", "untrusted_plugin")
    monkeypatch.setenv("PYTEST_ADDOPTS", "--collect-only")
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_targeted_test(workspace.path, timeout_seconds=7)

    assert result.status == "passed"
    assert captured["args"] == fixed_test_argv()
    assert captured["shell"] is False
    assert captured["cwd"] == workspace.path
    assert captured["timeout"] == 7
    assert captured["env"]["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert "PYTEST_PLUGINS" not in captured["env"]
    assert "PYTEST_ADDOPTS" not in captured["env"]


def test_nonzero_exit_is_failure(monkeypatch):
    workspace = create_fresh_workspace()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="assert 80 == 90", stderr=""
        ),
    )

    result = run_targeted_test(workspace.path)

    assert result.status == "failed"
    assert result.return_code == 1


def test_timeout_is_failure_not_success(monkeypatch):
    workspace = create_fresh_workspace()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="still running")

    monkeypatch.setattr(subprocess, "run", timeout)
    result = run_targeted_test(workspace.path, timeout_seconds=1)

    assert result.status == "timed_out"
    assert result.return_code is None
    assert result.stdout == "still running"


def test_runner_refuses_workspace_outside_controlled_root(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        run_targeted_test(tmp_path)
