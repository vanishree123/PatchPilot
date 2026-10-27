"""Gemini Interactions adapter. This module never executes model output."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Mapping

import httpx
from google import genai
from google.genai import errors, types

from ..config import Settings
from .base import RepairProviderError


REPAIR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "function_source": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["function_source", "explanation"],
    "additionalProperties": False,
}

_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
logger = logging.getLogger(__name__)


def _log_request_result(
    started: float,
    *,
    outcome: str,
    exception_type: str,
    status: int | None,
    request_id: str | None,
) -> None:
    # Deliberately log metadata only. Do not pass SDK exceptions, headers, or bodies.
    logger.info(
        "Gemini Interactions request %s elapsed_ms=%d exception_type=%s http_status=%s request_id=%s",
        outcome,
        int((time.perf_counter() - started) * 1000),
        exception_type,
        status if status is not None else "none",
        request_id if request_id is not None else "none",
    )


def _status_code(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    for candidate in (
        getattr(exc, "status_code", None),
        getattr(exc, "code", None),
        getattr(response, "status_code", None),
    ):
        if isinstance(candidate, int) and not isinstance(candidate, bool):
            return candidate
    return None


def _request_id(exc: Exception) -> str | None:
    """Read only the SDK's documented correlation header, never dump headers."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None or not callable(getattr(headers, "get", None)):
        return None
    value = headers.get("x-request-id")
    if isinstance(value, str) and _SAFE_REQUEST_ID.fullmatch(value):
        return value
    return None


def _server_error_detail(exc: Exception) -> str:
    """Map known server wording to safe categories; never display raw body text."""
    candidates: list[str] = []
    message = getattr(exc, "message", None)
    if isinstance(message, str):
        candidates.append(message)
    for field in ("body", "details"):
        body = getattr(exc, field, None)
        if not isinstance(body, Mapping):
            continue
        error = body.get("error")
        if isinstance(error, Mapping) and isinstance(error.get("message"), str):
            candidates.append(error["message"])
        if isinstance(body.get("message"), str):
            candidates.append(body["message"])

    for candidate in candidates:
        normalized = candidate.casefold()
        if any(word in normalized for word in ("overload", "overloaded", "capacity")):
            return "Google reported a temporary capacity or overload condition"
        if any(word in normalized for word in ("unavailable", "temporarily", "try again")):
            return "Google reported temporary service unavailability"
        if any(word in normalized for word in ("internal", "backend", "server error")):
            return "Google reported an internal server error"
    return "Google returned an internal server error; raw details were withheld"


def _safe_server_error_message(exc: Exception, code: int | None) -> str:
    prefix = (
        f"Gemini server error (HTTP {code})"
        if code is not None
        else "Gemini internal server error"
    )
    message = f"{prefix}: {_server_error_detail(exc)}."
    request_id = _request_id(exc)
    if request_id:
        message += f" Request ID: {request_id}."
    return message


def _safe_api_error_message(exc: errors.APIError) -> str:
    """Translate structured SDK error fields into safe, useful diagnostics."""
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", "")
    status = status.upper() if isinstance(status, str) else ""
    detail = getattr(exc, "message", "")
    detail = detail.casefold() if isinstance(detail, str) else ""

    invalid_key = any(
        phrase in detail
        for phrase in (
            "api_key_invalid",
            "api key not valid",
            "invalid api key",
            "api key is invalid",
        )
    )
    missing_model = any(
        phrase in detail
        for phrase in ("model not found", "model is not found", "unknown model")
    )

    if code == 429 or status == "RESOURCE_EXHAUSTED":
        return "Gemini quota or rate limit reached (HTTP 429). Check AI Studio usage and quota."
    if code == 401 or status == "UNAUTHENTICATED" or invalid_key:
        return "Gemini authentication failed. Check that GEMINI_API_KEY is valid and active."
    if code == 403 or status == "PERMISSION_DENIED":
        return "Gemini access was denied. Check API-key restrictions and project access."
    if code == 404 or status == "NOT_FOUND" or missing_model:
        return "Configured Gemini model or API endpoint was not found. Check the model ID and API availability."
    if code in (408, 504) or status == "DEADLINE_EXCEEDED":
        return "Gemini generation timed out before a repair was returned."
    if code == 400 or status == "INVALID_ARGUMENT":
        return "Gemini rejected the request or JSON schema. Check the SDK/API request format and model structured-output support."
    if isinstance(code, int) and 500 <= code < 600:
        return _safe_server_error_message(exc, code)
    if isinstance(code, int):
        return f"Gemini API error (HTTP {code}) before a repair was returned; details were withheld."
    return "Gemini API returned an unclassified error before a repair was returned; details were withheld."


class GeminiProvider:
    """Call the configured Gemini model with one fixed synthetic code example."""

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise RepairProviderError("GEMINI_API_KEY is not configured.")
        self._settings = settings

    def generate_repair(self, source: str, expected_behavior: str) -> str:
        started = time.perf_counter()
        prompt = (
            "Fix this function so the expected behavior holds. Return only JSON "
            "matching response_format: function_source (replacement function only) "
            "and a short explanation. No imports, extra definitions, paths, commands, "
            "or markdown.\n"
            f"Expected behavior: {expected_behavior}\n"
            f"Function:\n{source.strip()}"
        )
        client = None
        try:
            client = genai.Client(
                api_key=self._settings.gemini_api_key,
                http_options=types.HttpOptions(
                    timeout=self._settings.gemini_request_timeout_ms,
                    # The pinned Interactions adapter maps attempts directly to
                    # max_retries; zero means one initial request and no retry.
                    retry_options=types.HttpRetryOptions(attempts=0),
                ),
            )
            interaction = client.interactions.create(
                model=self._settings.gemini_model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": REPAIR_RESPONSE_SCHEMA,
                },
            )
        except Exception as exc:
            # google-genai 2.32 wraps transport timeouts in its compatibility
            # APIConnectionError hierarchy, not httpx.TimeoutException or the
            # public google.genai.errors.APIError class.
            sdk_error_types = {base.__name__ for base in type(exc).__mro__}
            if (
                isinstance(exc, (httpx.TimeoutException, TimeoutError))
                or "APITimeoutError" in sdk_error_types
            ):
                message = "Gemini request timed out before a repair was returned."
            elif isinstance(exc, httpx.RequestError) or "APIConnectionError" in sdk_error_types:
                message = (
                    "Gemini network request failed before a repair was returned. "
                    "Check the network connection and proxy settings."
                )
            elif "InternalServerError" in sdk_error_types:
                message = _safe_server_error_message(exc, _status_code(exc))
            elif isinstance(exc, errors.APIError):
                message = _safe_api_error_message(exc)
            elif _status_code(exc) is not None and _status_code(exc) >= 500:
                message = _safe_server_error_message(exc, _status_code(exc))
            else:
                # SDK exception text may contain request data or credentials.
                exception_type = type(exc).__name__
                if exception_type in {"ValidationError", "TypeError", "ValueError"}:
                    message = (
                        "Gemini SDK rejected the local request configuration "
                        f"({exception_type}); check SDK/API compatibility and the JSON schema."
                    )
                else:
                    message = (
                        "Gemini request failed before a repair was returned "
                        f"({exception_type}); underlying details were withheld."
                    )
            status_code = _status_code(exc)
            logger.warning(
                "Gemini Interactions request failed elapsed_ms=%d exception_type=%s http_status=%s request_id=%s",
                int((time.perf_counter() - started) * 1000),
                type(exc).__name__,
                status_code if status_code is not None else "none",
                _request_id(exc) or "none",
            )
            raise RepairProviderError(message) from None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    # Closing a local HTTP client must not mask the request outcome.
                    pass

        output_text = getattr(interaction, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            _log_request_result(
                started,
                outcome="failed",
                exception_type="EmptyResponse",
                status=None,
                request_id=None,
            )
            raise RepairProviderError(
                "Gemini returned no repair text; no patch was available."
            )
        _log_request_result(
            started,
            outcome="succeeded",
            exception_type="none",
            status=None,
            request_id=None,
        )
        return output_text
