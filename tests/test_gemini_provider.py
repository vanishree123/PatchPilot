"""Gemini adapter unit tests use mocks only; they make no API requests."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest
from google.genai import errors, types
from google.genai._gaos.google_genai import _translate_retry_config
from google.genai._gaos.lib.compat_errors import APITimeoutError
from google.genai._gaos.lib.compat_errors import InternalServerError

from patchpilot.config import Settings
from patchpilot.providers.gemini_provider import (
    REPAIR_RESPONSE_SCHEMA,
    GeminiProvider,
)
from patchpilot.providers.base import RepairProviderError


def _settings(*, key="test-only-mock-key"):
    return Settings("gemini", "configured-test-model", key, 12345, 10)


def test_pinned_interactions_adapter_zero_attempts_means_no_retries():
    retry_config = _translate_retry_config(
        types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=0))
    )

    assert retry_config.max_retries == 0


def test_mocked_sdk_request_uses_interactions_json_schema_timeout_and_no_tools():
    mock_client = Mock()
    mock_client.interactions.create.return_value = SimpleNamespace(
        output_text='{"function_source":"def apply_discount(price):\\n return price * 0.9", "explanation":"Apply once."}'
    )
    with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client) as sdk:
        raw = GeminiProvider(_settings()).generate_repair(
            "def apply_discount(price): return price - price * 0.2",
            "100 returns 90",
        )

    assert raw.startswith('{"function_source"')
    sdk_kwargs = sdk.call_args.kwargs
    assert sdk_kwargs["api_key"] == "test-only-mock-key"
    assert sdk_kwargs["http_options"].timeout == 12345
    assert sdk_kwargs["http_options"].retry_options.attempts == 0
    request = mock_client.interactions.create.call_args.kwargs
    assert request["model"] == "configured-test-model"
    assert "100 returns 90" in request["input"]
    assert request["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": REPAIR_RESPONSE_SCHEMA,
    }
    assert "tools" not in request
    mock_client.close.assert_called_once_with()


def test_missing_key_fails_before_constructing_sdk_client():
    with patch("patchpilot.providers.gemini_provider.genai.Client") as sdk:
        with pytest.raises(RepairProviderError, match="not configured"):
            GeminiProvider(_settings(key=None))
    sdk.assert_not_called()


def test_mocked_request_timeout_maps_to_safe_message_without_secret():
    mock_client = Mock()
    mock_client.interactions.create.side_effect = httpx.ReadTimeout("sensitive detail")
    with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client):
        with pytest.raises(RepairProviderError, match="timed out") as exc_info:
            GeminiProvider(_settings()).generate_repair("source", "expected")
    assert "sensitive detail" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
    mock_client.close.assert_called_once_with()


def test_sdk_wrapped_api_timeout_error_logs_only_safe_diagnostics(caplog):
    mock_client = Mock()
    mock_client.interactions.create.side_effect = APITimeoutError(
        httpx.Request("POST", "https://example.invalid/interactions")
    )
    with caplog.at_level(logging.WARNING, logger="patchpilot.providers.gemini_provider"):
        with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client):
            with pytest.raises(RepairProviderError, match="request timed out") as exc_info:
                GeminiProvider(_settings()).generate_repair("source", "expected")
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
    assert "elapsed_ms=" in caplog.text
    assert "exception_type=APITimeoutError" in caplog.text
    assert "http_status=none" in caplog.text
    assert "request_id=none" in caplog.text
    assert "test-only-mock-key" not in caplog.text


@pytest.mark.parametrize(
    ("code", "status", "detail", "expected"),
    [
        (400, "INVALID_ARGUMENT", "structured-output schema invalid", "request or JSON schema"),
        (400, "INVALID_ARGUMENT", "API key not valid", "authentication failed"),
        (401, "UNAUTHENTICATED", "credential rejected", "authentication failed"),
        (403, "PERMISSION_DENIED", "access denied", "access was denied"),
        (404, "NOT_FOUND", "model not found", "model or API endpoint was not found"),
        (429, "RESOURCE_EXHAUSTED", "quota reached", "quota or rate limit"),
        (408, "DEADLINE_EXCEEDED", "deadline", "generation timed out"),
        (504, "DEADLINE_EXCEEDED", "deadline", "generation timed out"),
        (500, "INTERNAL", "private diagnostic token", "server error"),
    ],
)
def test_mocked_api_errors_are_classified_without_exposing_details(
    code, status, detail, expected
):
    mock_client = Mock()
    mock_client.interactions.create.side_effect = errors.APIError(
        code, {"error": {"status": status, "message": detail}}
    )
    with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client):
        with pytest.raises(RepairProviderError, match=expected) as exc_info:
            GeminiProvider(_settings()).generate_repair("source", "expected")
    assert detail not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_mocked_network_error_is_classified_without_exposing_details():
    mock_client = Mock()
    mock_client.interactions.create.side_effect = httpx.ConnectError(
        "test-only sensitive network detail"
    )
    with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client):
        with pytest.raises(RepairProviderError, match="network request failed") as exc_info:
            GeminiProvider(_settings()).generate_repair("source", "expected")
    assert "sensitive network detail" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_mocked_internal_server_error_logs_safe_status_and_request_id(caplog):
    mock_client = Mock()
    response = httpx.Response(
        500,
        headers={"x-request-id": "req-2026.test-123"},
        request=httpx.Request("POST", "https://example.invalid/interactions"),
    )
    mock_client.interactions.create.side_effect = InternalServerError(
        "raw response includes Authorization and prompt data",
        response=response,
        body={
            "error": {
                "message": (
                    "Internal server error; GEMINI_API_KEY=do-not-display "
                    "and request body=private-prompt"
                )
            }
        },
    )

    with caplog.at_level(logging.WARNING, logger="patchpilot.providers.gemini_provider"):
        with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client):
            with pytest.raises(RepairProviderError, match="HTTP 500") as exc_info:
                GeminiProvider(_settings()).generate_repair("source", "expected")

    message = str(exc_info.value)
    assert "internal server error" in message.lower()
    assert "Request ID: req-2026.test-123" in message
    assert "do-not-display" not in message
    assert "private-prompt" not in message
    assert "Authorization" not in message
    assert "elapsed_ms=" in caplog.text
    assert "exception_type=InternalServerError" in caplog.text
    assert "http_status=500" in caplog.text
    assert "request_id=req-2026.test-123" in caplog.text
    assert "GEMINI_API_KEY=do-not-display" not in caplog.text
    assert "private-prompt" not in caplog.text
    assert "Authorization" not in caplog.text
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_mocked_internal_server_error_omits_malformed_request_id():
    mock_client = Mock()
    response = httpx.Response(
        500,
        headers={"x-request-id": "bad id with spaces"},
        request=httpx.Request("POST", "https://example.invalid/interactions"),
    )
    mock_client.interactions.create.side_effect = InternalServerError(
        "Internal error",
        response=response,
        body={"error": {"message": "Internal error"}},
    )

    with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client):
        with pytest.raises(RepairProviderError) as exc_info:
            GeminiProvider(_settings()).generate_repair("source", "expected")

    assert "bad id" not in str(exc_info.value)
