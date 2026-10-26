---
doc: spec
status: approved
---

# PatchPilot — Technical Spec

## How This Works, In Plain Language

PatchPilot is a local Python app with a browser dashboard. Streamlit draws the dashboard and remembers the current demo’s stages and result history while that browser session is open. When the user starts the demo, PatchPilot copies the known-bug example into a temporary demo workspace and runs one fixed test there.

For an AI attempt, a separate repair service sends only the built-in example and its expected behavior to Gemini. Gemini must return structured JSON with a short explanation and one replacement `apply_discount` function. PatchPilot checks the JSON, the Python syntax tree, the permitted function shape, and the workspace boundary before writing the function into the demo copy. It never takes a path or shell command from the model.

The test runner always executes the same targeted pytest command with a timeout. If no AI patch can be returned because access is missing, unavailable, or generation times out, PatchPilot explains why and waits for the user to select **Try Predefined Demo Repair**. Once an AI patch has been returned, a rejected patch or failed verification remains visible; the user must choose the same action to start a fresh demo copy. Only a real passing targeted-test result counts as success.

This shape keeps the demo Python-only and easy to run on Windows. It is a narrow safety gate for one known function, not a general-purpose sandbox for arbitrary project code.

## The Core Journey Through the System

Implements `prd.md > The Core Journey`, `prd.md > Clearly Labeled Predefined Fallback`, and `prd.md > States and Boundaries`.

```text
Streamlit dashboard
  → workflow creates a fresh copy of the fixed example and test
  → fixed test shows the baseline failure (80, expected 90)
  → Gemini provider returns structured JSON, or generation cannot return a patch
  → local JSON, syntax-tree, function-shape, and file-boundary validation
  → validated function is applied only to the demo copy
  → fixed timed pytest command returns the actual result
  → dashboard shows provenance, reason, patch, validation, and result history
```

If Gemini cannot return a patch because it is not configured, unavailable, rate-limited, or times out during generation, the workflow explains the reason and waits for the user to select **Try Predefined Demo Repair**. If Gemini returns a patch that validation rejects, or a validated patch fails or times out during verification, PatchPilot keeps that AI attempt and reason visible and waits for the same explicit action. Any retry starts from a fresh copy of the original buggy fixture.

## Stack

- **Python 3.11 or newer** — shared baseline for the currently verified Streamlit, Google GenAI, and `python-dotenv` packages. Streamlit 1.66.1 requires Python 3.11 or newer; the Google SDK and `python-dotenv` currently require at least 3.10.
- **Streamlit 1.66.1** — the learner-approved Python dashboard choice. It renders the one-screen workflow and keeps its current stage and result history in `st.session_state` for the active browser session. Its trade-off is less fine-grained layout control than a custom HTML frontend. [Streamlit documentation](https://docs.streamlit.io/), [PyPI release and Python requirement](https://pypi.org/project/streamlit/).
- **Google GenAI SDK (`google-genai` 2.32.0)** — official Python client for the Gemini Developer API. The selected 2.32.0 release supports the Interactions API used here; its documented API supports `client.interactions.create`, the current JSON-schema `response_format`, and `types.HttpOptions(timeout=...)` in milliseconds. `gemini-3.8-flash` is the initial configurable model. Google’s current official model catalog lists this ID as a stable Gemini Developer API model and documents structured-output support. Keep `GEMINI_MODEL` configurable through `.env`, so the model can be changed without editing application code. [Gemini 3.8 Flash model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [model catalog](https://ai.google.dev/gemini-api/docs/models), [2.32.0 SDK release](https://github.com/googleapis/python-genai/releases/tag/v2.32.0), [official Python SDK documentation](https://googleapis.github.io/python-genai/), [Interactions API migration and structured-output examples](https://ai.google.dev/gemini-api/docs/migrate-to-interactions), and the [SDK timeout implementation](https://github.com/googleapis/python-genai/blob/v2.32.0/google/genai/_api_client.py).
- **`python-dotenv` 1.2.4** — loads local `.env` values for development while honoring already-set environment variables. [python-dotenv docs and PyPI release](https://pypi.org/project/python-dotenv/).
- **pytest 9.1.1** — the single targeted test runner used in the demo copy. [pytest docs](https://docs.pytest.org/en/stable/), [PyPI release](https://pypi.org/project/pytest/).
- Python standard library modules `ast`, `json`, `difflib`, `pathlib`, `shutil`, `hashlib`, and `subprocess` handle parsing, change display, workspace copies, preservation checks, and the fixed timed test process. [Python AST docs](https://docs.python.org/3/library/ast.html), [Python subprocess docs](https://docs.python.org/3/library/subprocess.html).

The listed package versions were available on 2026-10-26 and are starting pins for `requirements.txt`; check package compatibility again when building. No frontend framework, database, paid service, or deployment platform is required.

## Where It Runs and How Someone Tries It

PatchPilot runs on the learner’s Windows machine. Streamlit starts a local server and opens the dashboard in a browser at `http://localhost:8501`. The app needs internet access and a valid Gemini key for a real AI attempt. The predefined repair works without a key or paid account. Deployment is not part of this plan. The hackathon submission still requires a short demo video and a public GitHub repository; the local app is sufficient for recording.

Planned PowerShell setup and run commands (for a machine with Python 3.11+ and the Windows Python launcher):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add a Gemini API key for real model calls.
python -m streamlit run app.py
```

Open `http://localhost:8501`. To verify the built-in baseline manually, run the planned fixed test command from inside a fresh demo workspace; the original fixture is expected to fail with actual `80` versus expected `90`.

### Configuration

`.env.example` contains placeholders only:

```dotenv
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.8-flash
GEMINI_API_KEY=replace-with-your-own-key
GEMINI_REQUEST_TIMEOUT_MS=45000
TEST_TIMEOUT_SECONDS=10
```

`python-dotenv` loads `.env` locally before configuration is read. Production and terminal environment variables take precedence. `GEMINI_MODEL` remains configurable in `.env`; the current default ID is `gemini-3.8-flash`. The Gemini key is read only by the Python process and is never rendered in the dashboard, prompt, logs, fixture, or source control. The project `.gitignore` already ignores `.env` and `.env.*` while allowing `.env.example`; add `/runtime/demo_workspaces/` so generated copies and test output are not committed. Never ask the learner to paste a key into chat or a source file.

Gemini API setup: create or select a project and key in [Google AI Studio](https://aistudio.google.com/), accept the service terms, and put the key in the local `.env`. Google’s current key documentation says new AI Studio keys are authorization keys by default as of May 28, 2026. New Gemini API accounts start on a free tier with access to certain models. The current pricing table lists standard input and output for `gemini-3.8-flash` as free; the free tier may use prompts and responses to improve Google products. Its exact rate limits vary by project and are shown in AI Studio; they are not guaranteed. Only the built-in synthetic example is sent. [Gemini API key setup](https://ai.google.dev/gemini-api/docs/api-key), [billing and tiers](https://ai.google.dev/gemini-api/docs/billing), [model availability](https://ai.google.dev/gemini-api/docs/models), [pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Look and Feel

Carry forward `prd.md > Look and Feel`: a clean, professional dashboard with minimal navigation, readable code blocks, and clear workflow states. Use compact stage indicators, visible repair-source labels, and distinct success, failure, rejection, and timeout messages. No specific palette or font was selected; use Streamlit’s normal theme and restrained CSS only if needed to achieve this direction.

## Components

### Streamlit Dashboard (`app.py`)

Renders the title, built-in discount example, **Repair Demo Bug**, workflow stages, patch/diff, the active workflow’s transient result history, and **Reset Demo** / **Try Predefined Demo Repair** actions. It displays the precise provenance and failure reason supplied by the workflow service; after the fixed pytest test actually passes, it displays **Targeted test passed**. It does not imply the patch is universally correct or secure, call the model itself, or execute model-provided commands.

PRD refs: `prd.md > Screens and Layout`, `prd.md > Built-In Discount Repair Workflow`, `prd.md > Reset and Results`, `prd.md > States and Boundaries`.

### Workflow Coordinator (`patchpilot/workflow.py`)

Owns the ordered stages and branches. It creates the initial demo copy, runs the baseline, asks the repair service for a candidate, sends AI candidates through validation, runs verification, and returns result records to the UI. When no patch is returned because access is unavailable or generation fails, it reports the reason and offers a user-selected predefined repair. A returned patch that is rejected or fails verification also requires an explicit predefined retry.

PRD refs: `prd.md > The Core Journey`, `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > States and Boundaries`.

### Repair Service and Provider Interface (`patchpilot/repair_service.py`, `patchpilot/providers/base.py`)

Defines a small provider interface that accepts the fixed bug context and source and returns a normalized `RepairProposal` or a typed provider failure. The proposal contains provenance, explanation, and candidate function text. It has no command or path field. The repair service maps provider outcomes to the PRD’s exact labels and preserves failure reasons. This boundary allows another provider to be added later without changing the UI, validator, workspace manager, or test runner; only Gemini is in the MVP.

PRD refs: `prd.md > Built-In Discount Repair Workflow`, `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > Product Decisions`.

### Gemini Provider (`patchpilot/providers/gemini_provider.py`)

Reads the model, API key, and request timeout from validated configuration and uses the Google GenAI Python SDK pinned to `google-genai==2.32.0`. The call uses the Gemini Interactions endpoint through `client.interactions.create`: model `GEMINI_MODEL`, an input containing only the built-in function and expected `100 → 90` behavior, and a JSON response format with exactly `function_source` and `explanation`. Read `interaction.output_text` and validate it again locally. No tool use or code-execution feature is enabled.

Request endpoint documented by Google: `POST https://generativelanguage.googleapis.com/v1beta/interactions`. The SDK sends the API key as authentication; it must come from `GEMINI_API_KEY`. Configure `types.HttpOptions(timeout=GEMINI_REQUEST_TIMEOUT_MS)`; the selected SDK documents this timeout in milliseconds. The documented Interactions method accepts the structured `response_format` JSON-schema shape used here, and returns text through `interaction.output_text`. Keep the initial request timeout at 45 seconds and handle quota/rate-limit (`429 RESOURCE_EXHAUSTED`), other API errors, and timeouts without exposing the key. Disable automatic SDK retries for this interactive call so quota or transient failures reach the existing fallback logic promptly. These call, schema, and timeout details were checked against SDK 2.32.0 and Google’s official SDK/API documentation before implementation. [Gemini Interactions migration guide](https://ai.google.dev/gemini-api/docs/migrate-to-interactions), [Python SDK docs](https://googleapis.github.io/python-genai/), [SDK 2.32.0 timeout implementation](https://github.com/googleapis/python-genai/blob/v2.32.0/google/genai/_api_client.py).

PRD refs: `prd.md > Built-In Discount Repair Workflow`, `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > States and Boundaries`.

### Patch Validator (`patchpilot/patch_validator.py`)

Validates before any write to a demo copy:

1. Require a valid JSON object with exactly `function_source` and `explanation`, both strings. Reject markdown fences, extra keys, paths, commands, missing fields, malformed JSON, and oversized responses.
2. Parse `function_source` with Python’s `ast.parse`; parsing inspects syntax without executing it.
3. Require an `ast.Module` containing exactly one `ast.FunctionDef` named `apply_discount`. Require no decorators, type parameters, return annotation, or type comment. Its `ast.arguments` must contain exactly one `ast.arg` named `price`, with no positional-only, keyword-only, variadic, defaults, or keyword defaults. Its body must contain exactly one `ast.Return` with a value. The function structure therefore explicitly permits only `Module`, `FunctionDef`, `arguments`, `arg`, and `Return` nodes, plus the expression nodes listed below.
4. The return expression may use only `ast.BinOp` with `ast.Add`, `ast.Sub`, `ast.Mult`, or `ast.Div`; `ast.UnaryOp` with `ast.UAdd` or `ast.USub`; `ast.Name` for `price` with `ast.Load` context; and numeric `ast.Constant` values (integer or float, excluding booleans and complex numbers). Parentheses require no separate node in Python’s AST. Explicitly reject every node not in this allowlist, including `ast.Call`, `ast.Attribute`, `ast.Assign`, `ast.Import`, `ast.ImportFrom`, additional function/class definitions, control flow, comprehensions, strings, and all other contexts/operators. Also validate each node’s fields and enforce reasonable source and explanation length limits.
5. Bind the destination in application code to the one expected demo source file. Do not accept a model-selected path. Resolve the final target and confirm it remains inside the fresh demo workspace; generate the displayed diff locally.

The allowlist is intentionally narrow and may reject another mathematically valid coding style. A rejection is visible as **AI-Generated — Patch Rejected**; the candidate is not applied, and the user chooses whether to try the predefined repair. Structured output and AST validation are guardrails, not a proof that code is safe in every Python environment.

PRD refs: `prd.md > Built-In Discount Repair Workflow`, `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > States and Boundaries`.

### Demo Workspace Manager (`patchpilot/workspace.py`)

Keeps `examples/buggy_discount.py` as the immutable source fixture. Record its SHA-256 before the workflow attempt and verify it remains unchanged after the complete attempt, including any explicit fallback. If the hash differs, report a source-preservation failure and do not report the workflow as successful, even if the targeted test passed. For the baseline and every repair attempt, copy the fixture and fixed `tests/test_discount.py` into a new workspace under `runtime/demo_workspaces/<run-id>/`; all repair writes target only the appropriate fresh demo workspace copy. Only the validator may write `buggy_discount.py` inside that workspace. The test file is copied from the repository and never changed. A fallback after an AI attempt gets a new copy from the original buggy fixture, not the AI-modified copy. Reset makes a fresh copy. Never copy data from an arbitrary user path.

PRD refs: `prd.md > The Core Journey`, `prd.md > Built-In Discount Repair Workflow`, `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > Reset and Results`.

### Predefined Repair (`patchpilot/predefined_repair.py`)

Stores the known repair for the discount demo in project-owned code, not in a provider response. Send it through the same JSON/function validation and workspace boundary checks before applying it. Every result is labeled exactly **Predefined Demo Repair — Not AI-Generated**. It is callable only for this built-in scenario.

PRD refs: `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > Product Decisions`.

### Fixed Test Runner (`patchpilot/test_runner.py`)

Runs only the preselected targeted command in the controlled workspace, with an argument list and no shell:

```python
[sys.executable, "-m", "pytest", "tests/test_discount.py", "-q"]
```

Build a child environment in application code, set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and remove `PYTEST_PLUGINS` and `PYTEST_ADDOPTS` so inherited plugin or extra-option settings cannot alter the fixed run. Pass it as `env=child_env` to `subprocess.run(..., cwd=workspace, shell=False, capture_output=True, text=True, timeout=TEST_TIMEOUT_SECONDS)`. Do not accept arguments, paths, scripts, environment changes, or commands from Gemini. Capture the return code and output. A nonzero exit means verification failed. `TimeoutExpired` means timed out, never passed. The configured initial timeout is 10 seconds. The fixed argv, disabled automatic plugin loading, controlled workspace, and timeout reduce risk; they do not create a complete OS-level sandbox for arbitrary untrusted code. Python documents subprocess timeout behavior; pytest documents its invocation and plugin autoload controls. [Python subprocess timeout](https://docs.python.org/3/library/subprocess.html), [pytest invocation](https://docs.pytest.org/en/stable/how-to/usage.html), [pytest plugin loading](https://docs.pytest.org/en/stable/how-to/plugins.html).

PRD refs: `prd.md > Built-In Discount Repair Workflow`, `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > States and Boundaries`.

### Configuration (`patchpilot/config.py`)

Loads `.env` for local development and validates configuration at startup. `AI_PROVIDER` selects the registered provider (initially `gemini`); `GEMINI_MODEL` selects the model. Missing `GEMINI_API_KEY` is a handled “real AI unavailable” case and keeps the built-in demo available through a user-selected labeled fallback. Validate the request and test timeouts as positive, bounded numbers. Never log secret values.

PRD refs: `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > Product Decisions`, `prd.md > States and Boundaries`.

## Data Model

No database or cross-session persistence is needed. Streamlit `st.session_state` holds only the active workflow and its transient attempt history for the current browser session:

- `run_id` and current workflow stage;
- each attempt’s provenance (`ai_generated` or `predefined`), outcome label, reason, explanation, and local diff;
- validation result and message;
- test status (`passed`, `failed`, `timed_out`, or `not_run`), exit code where available, and bounded stdout/stderr;
- the current demo workspace path (never supplied by the model).

Each attempt appends a result record within the current workflow; a user-selected predefined retry does not overwrite the AI failure and its reason. **Reset Demo** starts a clean run, creates a fresh workspace, and clears the previous run’s transient result history. No cross-run or persistent history is introduced. Streamlit session state is tied to the browser’s WebSocket session and may clear on a reload or new session. [Streamlit Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state).

## File Structure

```text
PatchPilot-Hackathon/
├── app.py                              # Streamlit dashboard and event handlers
├── patchpilot/
│   ├── config.py                       # Environment variables and validation
│   ├── workflow.py                     # Ordered stages, branches, result history
│   ├── repair_service.py                # Provider-neutral repair orchestration
│   ├── patch_validator.py               # JSON, AST, and file-boundary checks
│   ├── workspace.py                     # Fresh/reset controlled demo copies
│   ├── predefined_repair.py              # Labeled repair for the one fixture
│   ├── test_runner.py                    # Fixed timed pytest process
│   └── providers/
│       ├── base.py                       # Provider interface and normalized results
│       └── gemini_provider.py            # Google GenAI SDK integration
├── examples/
│   └── buggy_discount.py                 # Immutable original bug fixture
├── tests/
│   └── test_discount.py                  # Fixed targeted test copied to each workspace
├── runtime/
│   └── demo_workspaces/                  # Generated copies; ignored by Git
├── .env.example                          # Secret-free configuration placeholders
├── .gitignore                            # Ignores .env and generated demo workspaces
├── requirements.txt                      # Direct dependencies with planned pins
├── README.md                             # Windows setup, config, run, and demo steps
└── devpost/
    ├── learner-profile.md                # Ignored personal learning context
    ├── scope.md                          # Approved project scope
    ├── prd.md                            # Approved product requirements
    └── spec.md                           # This technical plan
```

## External Services and Dependencies

### Gemini Developer API

- **Service/provider:** Google Gemini Developer API, initially via `gemini-3.8-flash`; provider/model are environment-configurable. Verified against Google’s current official model catalog: `gemini-3.8-flash` is listed as a stable Gemini Developer API model and its model page lists structured outputs as supported. Rate limits vary by project and may change, so confirm the active limit in AI Studio before recording. Free-tier input may be used to improve Google products; only the synthetic built-in fixture is sent. [Official model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [model catalog](https://ai.google.dev/gemini-api/docs/models).
- **Setup:** create/select an AI Studio project and API key, set `GEMINI_API_KEY` in the local `.env`, and use `GEMINI_MODEL=gemini-3.8-flash`. Review current account pricing and billing before making a live call; free-tier availability can vary. If access, model availability, quota, or the request fails before a patch is returned, display the specific reason and wait for the user to select the predefined fallback.
- **Call:** SDK method `client.interactions.create(model=GEMINI_MODEL, input=<fixed bug context and source>, response_format=<JSON schema>)`, which uses `POST https://generativelanguage.googleapis.com/v1beta/interactions`. The schema asks only for `function_source` and `explanation`; local validation independently rejects extra or malformed output.
- **Authentication:** environment key only, via `GEMINI_API_KEY`; the SDK sends it to Google. Never put it in the client UI, prompt, test output, or source control.
- **Limits/errors:** Google enforces project-level requests-per-minute, input-tokens-per-minute, and requests-per-day limits. Current project/model values appear in AI Studio and are not guaranteed. A `429 RESOURCE_EXHAUSTED`, missing key, API error, or generation timeout before a patch returns an explanatory unavailable state and offers the labeled predefined fallback for explicit user selection. A returned but rejected/failed patch is a separate AI attempt; it is retained and requires user-controlled fallback.
- **Documentation:** [models](https://ai.google.dev/gemini-api/docs/models), [pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [API key](https://ai.google.dev/gemini-api/docs/api-key), [structured output](https://ai.google.dev/gemini-api/docs/structured-output), [getting started](https://ai.google.dev/gemini-api/docs/get-started?lang=python).

### Python Dependencies

- [Streamlit 1.66.1](https://pypi.org/project/streamlit/) — dashboard; [running locally](https://docs.streamlit.io/develop/concepts/architecture/run-your-app), [session state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state).
- [google-genai 2.32.0](https://pypi.org/project/google-genai/) — official Gemini Python client; [SDK reference](https://googleapis.github.io/python-genai/).
- [python-dotenv 1.2.4](https://pypi.org/project/python-dotenv/) — local `.env` loading; environment variables already present take precedence by default.
- [pytest 9.1.1](https://pypi.org/project/pytest/) — fixed targeted test and development verification.
- Python 3.11+ standard library — `ast`, `json`, `subprocess`, `pathlib`, `shutil`, `hashlib`, and `difflib`.

## Important Failure Modes

- **Missing key / unavailable model / quota (`429`) / API failure / generation timeout before a patch is returned** → show the exact reason, state that no AI patch was returned, and offer **Try Predefined Demo Repair**. Apply it only after the user selects the action, in a fresh demo copy, with label **Predefined Demo Repair — Not AI-Generated**.
- **Malformed JSON, extra fields, invalid syntax, unexpected syntax, or a patch boundary violation after a candidate is returned** → label it **AI-Generated — Patch Rejected**, display the precise rejection reason, do not write it, keep it in history, and offer **Try Predefined Demo Repair** separately.
- **Valid AI patch but targeted test failure** → label it **AI-Generated — Verification Failed**, display actual output, keep the record, and wait for the user’s separate fallback action.
- **Valid AI patch but targeted test timeout** → label it **AI-Generated — Verification Failed (Test Timed Out)**, show timeout, do not claim success, keep the record, and offer the separate fallback action.
- **Predefined repair validation/test failure or timeout** → show its actual validation/test outcome under **Predefined Demo Repair — Not AI-Generated**; never display success unless the targeted test actually passed.
- **Workspace escape, missing fixture, or source mismatch** → stop before writing/running a test, show a workspace error, and preserve the original fixture. The application does not run model-provided commands or paths.

## Testing Strategy

These are planned checks for the build; none has been run yet. The PatchPilot app’s runtime runner remains restricted to its single fixed command: `python -m pytest tests/test_discount.py -q`.

- **Baseline and repair behavior:** the original fixture’s targeted test returns actual `80` against expected `90`; the predefined repair and an accepted AI repair produce `90` and a passing targeted test in their respective copies. The dashboard displays **Targeted test passed** only when the fixed test process actually exits successfully; this result is evidence for the example, not proof of universal correctness or security.
- **Provider/response validation:** accept only the expected JSON keys and a syntactically valid `apply_discount(price)` function; reject malformed JSON, fenced/non-JSON text, extra keys, path/command fields, imports, extra functions, calls, attributes, assignments, control flow, and disallowed operators.
- **Boundary and preservation:** record the original fixture’s SHA-256 before each workflow attempt and verify it after the complete attempt; test that a changed hash produces a visible source-preservation failure and prevents success reporting. Verify AI and fallback writes affect only the appropriate fresh workspace copy, the original fixture and test remain unchanged, and any destination outside the intended workspace file is rejected.
- **Failure-history branches:** verify model unavailability before a patch returns remains visible and offers an explicit labeled fallback; verify a returned invalid patch, failed test, or timeout remains visible as a distinct AI result and does not auto-fallback; verify the explicit button starts a new original-based copy while retaining the previous result within that same workflow; verify **Reset Demo** clears transient history and starts a clean run.
- **Test runner:** verify the argument list is fixed, `shell=False`, working directory is the demo copy, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` is set by application code, `PYTEST_PLUGINS` and `PYTEST_ADDOPTS` are removed from the child environment, no model-supplied environment change is accepted, captured test output is shown, timeout is reported as failure, and arbitrary command strings are never accepted. Unit-test timeout handling by mocking the process call rather than executing a different command from the app.
- **AST validator:** include positive tests for the intended arithmetic repair and other allowed forms satisfying the fixture, plus negative tests for missing or extra arguments, extra functions, imports, calls, attributes, assignments, nonnumeric constants, boolean/complex constants, unsupported operators, non-`Load` names, decorators, annotations, control flow, and extra statements. Assert rejected source is never written.
- **Configuration/security:** missing key keeps the demo usable; provider/model values are configurable; `.env` and API-key values never appear in Git-tracked files, UI, or logs; `.env.example` contains placeholders only.
- **Manual end-to-end review:** run the real Gemini path when an eligible key/quota is available, and the no-key predefined path when it is not. Confirm labels and recorded reasons exactly match the path taken.

## What Was Simplified and Why

- One bundled discount fixture instead of arbitrary repository uploads — limits the model context, patch target, and test to the exact proof of concept.
- One function-only response with an AST allowlist instead of general patches — makes the model boundary narrow and reviewable; alternative valid styles can be rejected.
- One initial Gemini adapter behind a provider interface instead of several live model integrations — demonstrates genuine model use while keeping a future provider change localized.
- One workflow’s transient result history instead of a database or multi-run history — enough to preserve an AI failure while the user tries the fallback, and cleared by **Reset Demo**.
- Local Streamlit run instead of deployment — enough for the required screen recording and public repository, with less setup.

## Decisions and Open Issues

- **Learner choice:** Python-only Streamlit dashboard, local Windows run, and hosted model API; accepted because this fits Python experience and the deadline.
- **Learner choice:** Gemini is the first provider, with provider and model configurable. The current official model page verifies stable `gemini-3.8-flash` availability and structured-output support through the Gemini Developer API; usage limits remain project-specific and must be checked in AI Studio.
- **Learner choice:** structured JSON contains only a function replacement and explanation. No model-supplied path, command, or arbitrary execution instructions are allowed.
- **Learner choice:** patch validation and verification failures after a returned AI patch remain visible; the predefined fallback is user-controlled and starts from a fresh original-based copy.
- **Learner choice:** runtime test command is fixed, uses no shell, and has a configured timeout; only an actual pass is success.
- **Learning moment:** the model’s JSON schema is only an output guide. The local JSON and AST allowlist performs the actual accept/reject check before any write. Verify this boundary in the planned validator tests.
- **Documented trade-off:** the narrow function and arithmetic allowlist may reject a valid repair written in a different style. That rejection is shown and the user can choose the predefined repair.
- **Configuration verified before implementation:** the pinned `google-genai==2.32.0` supports the documented Interactions API call, JSON-schema `response_format`, and `HttpOptions.timeout` in milliseconds. At build start, confirm the learner’s Python is 3.11+, install the pins, and check current Gemini free-tier access/rate limits in AI Studio. If free-tier access is unavailable, finish and demonstrate the clearly labeled predefined workflow; document how to enable Gemini by adding the API key later.
- **Runtime limits:** the 45-second model request timeout and 10-second test timeout are configurable starting defaults chosen to keep a demo attempt bounded. Adjust them if local behavior or live provider responses show they are unsuitable, while preserving a visible timeout result.
