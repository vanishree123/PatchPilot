# Contributing

Thanks for taking an interest in PatchPilot. This is a small, local proof of concept; changes should preserve its narrow scope and safety rules.

## Set up

Use Python 3.11 or newer and follow the Windows setup in [README.md](README.md). Install the pinned dependencies from `requirements.txt`. A Gemini key is not needed for offline development or tests.

## Before opening a change

1. Read [Architecture](docs/ARCHITECTURE.md), [Security](docs/SECURITY.md), and [Testing](docs/TESTING.md).
2. Keep model responses untrusted. Preserve JSON parsing, the AST allowlist, workspace-root checks, fixed test command, `shell=False`, plugin controls, timeouts, and SHA-256 verification.
3. Keep provider tests mocked. Do not add tests that make live model requests or require a real API key.
4. Add or update tests for behavior changes and update user/developer documentation when behavior or setup changes.
5. Run the complete test suite and inspect the full diff before proposing the change.

## Run checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs
git diff --check
git status --short
```

Do not weaken tests or represent mocked output as genuine AI generation. Do not include `.env`, API keys, local workspaces, virtual environments, caches, screenshots containing credentials, or unrelated learner/agent files in a contribution.

## Contribution workflow

Use a focused branch and change set. Explain the user-visible behavior, safety impact, tests run, and any test limitations in the pull request. Review staged files by name before committing. Do not force-push or rewrite shared history. There is no contribution-specific code of conduct or additional governance document in this MVP.
