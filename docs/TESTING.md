# Testing

## Run the suite

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs
```

After a fresh setup, the same command works once dependencies are installed into `.venv`. The repository's `pytest.ini` selects `tests/` and excludes runtime workspaces and the virtual environment from collection.

## What the tests cover

| Test module | Coverage |
| --- | --- |
| `tests/test_config.py` | Defaults, environment configuration, timeout bounds, and key handling without printing the value. |
| `tests/test_gemini_provider.py` | Mocked Interactions request, JSON schema, timeout/retry settings, safe error categories, and diagnostics. No live API requests. |
| `tests/test_repair_service.py` | No-key handling, mocked provider errors, malformed JSON, rejected candidates, and provenance labels. |
| `tests/test_patch_validator.py` | Accepted function structure and rejection of extra JSON keys, duplicate keys, imports, calls, and disallowed syntax. |
| `tests/test_workspace.py` | Fresh workspace copies and original fixture preservation. |
| `tests/test_test_runner.py` | Fixed command, `shell=False`, controlled pytest environment, failure/timeout reporting, and workspace boundary. |
| `tests/test_workflow.py` | Baseline failure, successful predefined repair, mock AI branches, explicit fallback/retry history, reset-relevant state, and source-hash failure. |
| `tests/test_dashboard.py` | Dashboard states, explicit predefined retry, attempt history, and reset behavior using test doubles. |

The `tests/conftest.py` autouse fixture disables dotenv loading during tests. Provider tests use explicitly labeled mocks/fakes and synthetic values. They do not send HTTP requests or demonstrate genuine AI generation.

## Fixed test skip

`tests/test_discount.py` is copied into each controlled workspace and imported from there by the fixed runner. When pytest collects it from the repository root, `buggy_discount` is not importable, so the module deliberately skips with the message that it only runs from the controlled demo workspace. This is expected; the end-to-end workflow invokes it in the workspace.

## Current verified result

On 2026-10-27, the complete offline suite was run with `python -m pytest -q` and reported **53 passed, 1 skipped, 1 warning**. The skip is the controlled-workspace discount test described above. The warning comes from `google-genai` using a deprecated Python typing alias slated for removal in Python 3.17. The fixture hash was separately checked as `2E1E631D991BA35EFC657CDE890DCA037655F669A76E1B30B337AE2F4720A50B`.

This result should be refreshed by running the command above after changes. Offline tests verify local code and mocked request handling only. They do not verify API credentials, current model access, quota, network availability, or a live Gemini-generated repair. The latest live outcome reported by the owner was HTTP 503; a successful live repair has not been verified.
