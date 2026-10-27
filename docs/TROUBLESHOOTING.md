# Troubleshooting

## Streamlit does not start

Confirm the current directory is the repository root, then check Python and dependencies:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Use Python 3.11 or newer. If `.venv` was created with a removed or incompatible interpreter, recreate that project environment using a supported Python version; do not uninstall or modify your system Python. Streamlit prints the local address when startup succeeds. If port 8501 is occupied, use `--server.port 8502`.

## Gemini is not configured

Copy `.env.example` to `.env`, enter a valid key locally, save the file, and start a fresh Streamlit process. Do not paste the key into chat or print the `.env` file to troubleshoot. The `.env` file is ignored by Git. If the dashboard says the key is missing, ensure the file is in the repository root and the variable is named exactly `GEMINI_API_KEY`.

The model can be changed through `GEMINI_MODEL`. Confirm that the chosen ID and requested structured-output feature are currently available for the Gemini Developer API and your account before testing. No model name should be treated as available solely because it appears in the template.

## Timeout, HTTP 500, or HTTP 503

- **Timeout:** The configured request timeout defaults to 90,000 ms. The provider currently disables SDK retries for the interactive request. A timeout means no repair candidate was returned in time; it is not a successful repair.
- **HTTP 500:** Google documents this as an unexpected server error. It may be transient; it does not by itself establish whether the account, model, or service is the underlying cause.
- **HTTP 503:** Google documents this as temporary service unavailability/overload. Wait and check Google's service status before trying again. This app does not automatically retry the Gemini request.
- Check the current [Gemini API error guide](https://ai.google.dev/gemini-api/docs/api-errors), [troubleshooting guide](https://ai.google.dev/gemini-api/docs/troubleshooting), and [Google AI Studio status](https://aistudio.google.com/status).
- Avoid repeated clicks or rapid retries. A live request may consume quota or incur charges according to account settings.

The latest live outcome reported by the project owner was HTTP 503. This documentation pass and the offline suite made no live request. A successful Gemini-generated repair is not verified.

## Authentication, access, and quota

- **401/authentication:** Check that the local key is active and belongs to the intended project. If exposed, revoke it and replace it using Google AI Studio.
- **403/permission:** Check API access, project configuration, key restrictions, and account eligibility.
- **404/model:** Confirm the exact model ID and API availability in current official Google documentation.
- **429/quota or rate limit:** Check the selected project's AI Studio usage and limits. Wait for a limit reset or address account/billing configuration; do not put billing details in project files.

## Safe diagnostics

The application reports categorized errors without rendering the API key or raw response body. Provider logs are limited to elapsed request time, exception type, HTTP status, and a syntactically restricted request ID when available. When asking for help, share the dashboard's sanitized error and those metadata fields only. Never share `.env`, a key, authorization headers, raw environment output, or raw SDK exception dumps.

## Offline tests do not prove live availability

Run the offline suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs
```

Gemini provider tests use mocks. A passing suite does not verify the network, credentials, quota, model availability, or Google's service health. The only live verification is a user-triggered request from the dashboard whose returned repair passes validation, whose targeted test actually passes, and whose original fixture hash remains unchanged. The predefined repair is separately labeled and must be selected explicitly.
