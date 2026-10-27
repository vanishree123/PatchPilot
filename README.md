# PatchPilot

PatchPilot is a local proof of concept for inspecting and verifying a repair to one deliberately buggy Python function. It is aimed at Python developers and QA automation engineers who want to see a small, bounded bug-repair workflow end to end.

The built-in shop example applies a 10% discount twice: `apply_discount(100)` returns `80`, while the expected result is `90`. PatchPilot shows that baseline failure, requests a candidate from Gemini when configured, checks the candidate, applies it to a disposable copy, and reports the actual result of the fixed targeted test.

> **Live Gemini status:** Real generation has not been verified successfully. The latest live result reported by the project owner was HTTP 503 (temporary service unavailability). Offline tests do not establish that Gemini is available.

## Features

- One deterministic discount bug, one fixed test, and one local Streamlit dashboard.
- Configurable Gemini model through the Interactions API with structured JSON output.
- Strict JSON and Python AST validation before a candidate can be written.
- A separate, explicitly selected **Predefined Demo Repair — Not AI-Generated** path. A failed or rejected Gemini attempt is not silently replaced.
- Repairs are written only into a fresh demo workspace. The original fixture is SHA-256 checked before and after each attempt.
- The runner executes only `python -m pytest tests/test_discount.py -q`, with argument-list process execution, `shell=False`, plugin autoload disabled, and a timeout.
- AI attempt history is transient within the current workflow. **Reset Demo** clears it.

## Workflow

1. **Baseline Test** runs against a fresh copy and shows the failure (`80`, expected `90`).
2. **Analyze Bug** and **Propose Repair** show the configured provider result and its provenance.
3. **Validate Patch** parses the exact JSON response and checks the replacement function against a narrow AST allowlist.
4. **Apply to Demo Copy** writes the validated function only to `buggy_discount.py` in a new workspace.
5. **Verify with Tests** runs the fixed targeted test and reports its real output and status.
6. If Gemini returns no candidate, or a returned candidate is rejected or fails verification, the dashboard presents the relevant reason. The user may choose **Try Predefined Demo Repair** as a separate action. It starts in a fresh copy and keeps the prior attempt in the current workflow history.

A passing targeted test is evidence for this example only. It does not prove universal correctness or security. See [Architecture](docs/ARCHITECTURE.md), [Security](docs/SECURITY.md), and [Testing](docs/TESTING.md) for details.

## Architecture

| Component | Responsibility |
| --- | --- |
| `app.py` | Streamlit dashboard, button handling, status display, and transient session history. |
| `patchpilot/workflow.py` | Coordinates baseline, repair attempt, explicit predefined retry, result history, and source-hash checks. |
| `patchpilot/repair_service.py` | Calls the configured repair provider, parses the response, and distinguishes unavailable, rejected, AI, and predefined results. |
| `patchpilot/providers/gemini_provider.py` | Sends the built-in function to Gemini using the Interactions API and structured JSON response format; sanitizes diagnostics. |
| `patchpilot/patch_validator.py` | Validates the JSON shape and AST allowlist, then writes only the approved function to a controlled copy. |
| `patchpilot/workspace.py` | Creates fresh copies of the original fixture and fixed test; calculates and checks SHA-256. |
| `patchpilot/test_runner.py` | Runs the fixed pytest argument list without a shell and classifies pass, failure, and timeout. |
| `patchpilot/config.py` | Loads provider, model, key, and timeout settings from the process environment and local `.env`. |

## Technology

- Python 3.11 or newer (the current project environment uses Python 3.14.5).
- Streamlit 1.66.1
- Google Gen AI Python SDK (`google-genai`) 2.32.0
- `python-dotenv` 1.2.4
- pytest 9.1.1

Pinned dependencies are listed in `requirements.txt`. A clean temporary virtual environment created with `py -3` successfully installed `requirements.txt` on Python 3.14.5 during this review, and `pip check` reported no broken requirements. Python 3.11 or newer is the documented minimum.

## Windows setup (PowerShell)

From the project directory, create a virtual environment and install the pinned dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the Python launcher is unavailable, create the environment with your installed Python 3.11+ executable, for example `python -m venv .venv`. You do not need to activate the environment when using the explicit `.venv\Scripts\python.exe` commands.

### Gemini configuration

Copy the template and edit `.env` locally:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `GEMINI_API_KEY` to your own Google AI Studio key. The template uses placeholders only. `.env` is ignored by Git; never paste the key into source code, chat, screenshots, issue reports, or logs. The model and timeouts are configurable:

```dotenv
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.8-flash
GEMINI_API_KEY=replace-with-your-own-key
GEMINI_REQUEST_TIMEOUT_MS=90000
TEST_TIMEOUT_SECONDS=10
```

Do not share or commit a populated `.env`. Check current model/API support, account access, quota, and pricing in the [Gemini API documentation](https://ai.google.dev/gemini-api/docs) before a live request. A user-triggered Gemini request may consume quota or incur charges depending on account and billing settings. No API call is made at app startup or by the offline test suite.

## Run PatchPilot

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`) and select **Repair Demo Bug**. With a key configured, this action can make one real Gemini request. The provider is configured with a 90,000 ms request timeout and automatic SDK retries disabled. A successful real Gemini repair has not yet been verified. If no candidate is returned, use the displayed failure and explicitly choose **Try Predefined Demo Repair** if you want the built-in fallback.

For a genuine Gemini result, confirm the dashboard labels the attempt **AI-Generated**, patch validation passes, the actual targeted test passes, and the original fixture hash is unchanged. Do not count a predefined repair or mocked test response as an AI result. A candidate that is rejected, fails its test, times out, or fails the source-integrity check is not a successful repair.

## Automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs
```

The `tests/test_gemini_provider.py` and workflow provider tests use explicitly marked mocks; they do not call Gemini. The fixed `tests/test_discount.py` is skipped when run from the repository root because its `buggy_discount` module is copied into, and executed from, a controlled demo workspace by PatchPilot. See [Testing](docs/TESTING.md) for test coverage and the latest verified results.

## Limitations and roadmap

- Only the built-in discount example is supported. There is no arbitrary repository upload or repair.
- The AST allowlist intentionally rejects many otherwise valid Python styles.
- A targeted test pass does not prove correctness for other inputs, correctness in production, or security.
- The demo workspace and subprocess controls reduce risk; they are not an operating-system sandbox for arbitrary untrusted programs.
- Gemini can be unavailable, rate limited, or return a rejected candidate. The predefined repair remains a distinct, user-selected path and is not evidence of AI generation.
- Live API behavior and current model/account availability depend on Google and account configuration. No successful live Gemini repair is claimed.

Possible later work, after reviewing the safety model, includes additional fixed examples, richer repair comparisons, and support for user-provided projects. These are not part of the current MVP.

## Project documents

- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [Testing](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Contributing](CONTRIBUTING.md)
- Planning artifacts: [scope](devpost/scope.md), [PRD](devpost/prd.md), [technical spec](devpost/spec.md), and [build checklist](devpost/checklist.md)

## License

This repository uses the Zero-Clause BSD (0BSD) license. It was chosen as a permissive license that does not require inserting an invented person or organization as the copyright holder. See [LICENSE](LICENSE).
