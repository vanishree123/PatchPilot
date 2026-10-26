# PatchPilot

PatchPilot is a local proof of concept for an inspectable repair of one built-in Python discount bug. The **Repair Demo Bug** dashboard action uses the configured Gemini provider when a key is present. A no-key or pre-response provider failure is shown clearly; the user then chooses **Try Predefined Demo Repair** to run the labeled fallback. A returned but invalid AI candidate is rejected and never written.

## Requirements

- Windows and Python 3.11 or newer. This project was prepared against Python 3.14.5; use the installed compatible Python in the commands below.
- Git for local version control.

## Setup (PowerShell)

From the project folder:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` is local and ignored by Git. Open it in a text editor and replace the placeholder for `GEMINI_API_KEY` with a key from Google AI Studio. Keep the key in `.env`; do not paste it into the application, chat, screenshots, or commit it. You can change `GEMINI_MODEL` there without editing Python code. The example defaults to `gemini-3.8-flash`.

The repair request sends only the built-in synthetic discount function and its expected behavior. The API call uses a 45-second timeout and does not retry automatically. Missing credentials, quota/rate limits, API errors, and generation timeouts are reported without showing the key. No API request occurs at app startup; selecting **Repair Demo Bug** with a configured key starts the model request. If no candidate returns, the dashboard does not apply a fallback automatically; the user explicitly chooses **Try Predefined Demo Repair**.

## Architecture and safety

`app.py` passes the user's dashboard action to `patchpilot.workflow.run_demo`. The workflow loads configuration, calls the provider-neutral repair service, and routes a configured request through `patchpilot.providers.gemini_provider`. The service strictly parses Gemini's JSON response and applies the AST allowlist before the workflow can write anything. Validated functions can only replace `apply_discount` in a fresh workspace copy; the original `examples/buggy_discount.py` is hashed before and after each attempt.

PatchPilot runs only `python -m pytest tests/test_discount.py -q` in the controlled demo workspace, with argument-list execution, `shell=False`, plugin autoload disabled, and a timeout. These checks reduce risk but are not an OS-level sandbox for arbitrary untrusted code. No model-provided commands, paths, or environment changes are accepted. A passing targeted test is evidence for this example only; it does not prove all cases work or establish universal correctness or security.

The predefined retry is a separate user action after Gemini is unavailable, returns no candidate, or returns a rejected/failed candidate. It starts from a fresh copy and retains the previous result in the current session. **Reset Demo** clears that transient history.

## Run the app

```powershell
python -m streamlit run app.py
```

Open `http://localhost:8501`, select **Repair Demo Bug**, and inspect the baseline failure, repair provenance label, validation result, targeted test output, and source-preservation status. A passing test verifies this example only; it does not prove universal correctness or security.

### Genuine Gemini demonstration

1. Configure a valid key in the local `.env` file as described above; never include it in a screenshot or recording.
2. Start the dashboard and select **Repair Demo Bug** once. This is the user-triggered Gemini API request.
3. Confirm the result is labeled **AI-Generated**, inspect the returned function and patch validation, and confirm the targeted test actually passes and the original SHA-256 matches.
4. If Gemini is unavailable or the candidate fails validation or verification, show the displayed failure and choose **Try Predefined Demo Repair** only if you want to continue with the clearly labeled fallback. Never call the fallback result AI-generated.

Model availability: Google currently lists `gemini-3.8-flash` as a stable Gemini Developer API model with structured-output support. Its pricing page lists a free tier and a paid tier (currently $0.75 per million input tokens and $3.75 per million output tokens through 2026-12-31); account eligibility and billing settings can differ. Review your account pricing before selecting **Repair Demo Bug** with a key configured. [Model availability](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) · [Pricing](https://ai.google.dev/gemini-api/docs/pricing).

## Run automated tests

```powershell
python -m pytest -q
```

Last verification on 2026-10-27: `python -m pytest -q -rs` completed with **41 passed, 1 skipped, 1 warning**. The skip is expected because the target discount test runs only inside a controlled demo workspace. The warning is a Google GenAI SDK deprecation warning for a Python typing alias slated for removal in Python 3.17. The original fixture SHA-256 remained `2E1E631D991BA35EFC657CDE890DCA037655F669A76E1B30B337AE2F4720A50B`.

The app's controlled test runner separately invokes only `python -m pytest tests/test_discount.py -q` in a fresh demo workspace, without a shell and with a timeout.

Tests of the Gemini adapter use a mocked SDK client. They verify request construction and error mapping without contacting Gemini; a mocked response is never presented as an actual AI-generated repair in the UI. No live Gemini request or result has been verified yet.
