"""Create disposable, original-based copies for each PatchPilot attempt."""

from __future__ import annotations

import hashlib
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_FIXTURE = REPOSITORY_ROOT / "examples" / "buggy_discount.py"
TARGETED_TEST = REPOSITORY_ROOT / "tests" / "test_discount.py"
WORKSPACE_ROOT = REPOSITORY_ROOT / "runtime" / "demo_workspaces"


@dataclass(frozen=True)
class DemoWorkspace:
    path: Path
    workspace_id: str


def sha256_file(path: Path = ORIGINAL_FIXTURE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_fresh_workspace() -> DemoWorkspace:
    if not ORIGINAL_FIXTURE.is_file() or not TARGETED_TEST.is_file():
        raise FileNotFoundError("Built-in fixture or targeted test is missing")
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    workspace_id = uuid.uuid4().hex
    workspace = WORKSPACE_ROOT / workspace_id
    workspace.mkdir()
    shutil.copy2(ORIGINAL_FIXTURE, workspace / "buggy_discount.py")
    test_dir = workspace / "tests"
    test_dir.mkdir()
    shutil.copy2(TARGETED_TEST, test_dir / TARGETED_TEST.name)
    return DemoWorkspace(path=workspace.resolve(), workspace_id=workspace_id)


def verify_original_hash(expected_hash: str) -> tuple[bool, str]:
    actual_hash = sha256_file()
    return actual_hash == expected_hash, actual_hash
