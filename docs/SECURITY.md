# Security and safety

PatchPilot is a constrained local proof of concept, not a general-purpose sandbox or autonomous repository editor.

## API key handling

- Store `GEMINI_API_KEY` in a local `.env` file or the process environment. Never hardcode it.
- `.env`, `.env.*`, and Streamlit secrets are ignored by Git; `.env.example` contains a placeholder, not a usable credential.
- Do not paste keys into chat, issue reports, screenshots, recordings, source files, or logs.
- If a key may have been exposed, revoke it in Google AI Studio, create a replacement there, update the local `.env`, and check usage/quota. Do not reuse the exposed key.
- The dashboard does not display the key. Provider logs contain request timing and sanitized metadata only, never raw SDK exception text, response bodies, or headers.
- The Gemini request sends only the built-in synthetic function and expected behavior. A live request may use quota or incur charges according to current account settings.

## Untrusted model output and validation

Gemini output is untrusted input. PatchPilot requires a JSON object containing exactly `function_source` and `explanation`, rejects duplicate/extra JSON keys, bounds input sizes, parses the Python source as an AST, and permits only one `apply_discount(price)` function with a narrow arithmetic return expression. Imports, extra definitions, file paths, shell commands, calls, attributes, assignments, and arbitrary execution instructions are rejected.

The AST allowlist reduces the accepted program shape but is intentionally restrictive and does not prove that a patch is correct or secure. Some otherwise valid Python implementations will be rejected. A successful targeted test verifies only this example.

## Workspace and process boundaries

- `examples/buggy_discount.py` is the immutable original fixture. PatchPilot hashes it before the workflow and checks it after each repair attempt. A mismatch blocks success.
- Every attempt writes only to a fresh directory under `runtime/demo_workspaces/`; the validator checks both the workspace root and permitted filename.
- The test runner executes only the fixed argument list `python -m pytest tests/test_discount.py -q`, uses `shell=False`, disables automatic pytest plugin loading, removes `PYTEST_PLUGINS` and `PYTEST_ADDOPTS` from the child environment, and applies a timeout.
- The child process otherwise inherits the application's environment. This is a controlled process setup, not a complete environment scrub or OS-level sandbox.
- The model cannot choose a command, path, test, environment variable, or workspace destination.

These measures reduce risk for this fixed fixture. They do **not** constitute a complete operating-system sandbox for arbitrary untrusted code. Do not use this MVP to repair production repositories or run arbitrary projects.

## Timeouts, retries, and failure handling

`GEMINI_REQUEST_TIMEOUT_MS` defaults to `90000`; `TEST_TIMEOUT_SECONDS` defaults to `10`. The pinned Gemini provider sets the SDK's Interactions retry attempts to zero because of the pinned SDK adapter's retry-count behavior. This avoids SDK retries multiplying interactive request duration, but it also means transient API failures are surfaced instead of retried automatically. The current setting does not guarantee a strict end-to-end wall-clock deadline for all local processing.

HTTP errors, network failures, timeouts, and invalid output are failures, not repair success. If Gemini returns no candidate, the app presents the failure and waits for the user to select the predefined repair. If a candidate is returned but rejected or fails verification, that AI attempt remains visible and fallback remains user-controlled. No failed or timed-out attempt is reported as successful.

## Threat model and remaining risks

Protected assets include the API key, the original fixture, user-visible repair provenance, and the integrity of test results. Relevant threats include accidental credential publication, hostile or malformed model output, path escape or unintended file edits, environment-injected pytest plugins/options, subprocess hangs, and presenting an unverified repair as successful. Controls are described above and covered by offline tests.

Remaining risks include vulnerabilities in Python, Streamlit, pytest, dependencies, the SDK, or the operating system; inherited environment variables in the child process; resource use by the local app; and errors that the single target test cannot detect. The API key is sent to Google's Gemini API when the user starts a model request. Treat model access and returned results accordingly. A passing targeted test is not a security certification.
