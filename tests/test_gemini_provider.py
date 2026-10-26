"""Gemini adapter unit tests use mocks only; they make no API requests."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest
from google.genai import errors

from patchpilot.config import Settings
from patchpilot.providers.gemini_provider import (
    REPAIR_RESPONSE_SCHEMA,
    GeminiProvider,
)
from patchpilot.providers.base import RepairProviderError


def _settings(*, key="test-only-mock-key"):
    return Settings("gemini", "configured-test-model", key, 12345, 10)


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
    assert sdk_kwargs["http_options"].retry_options.attempts == 1
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
    mock_client.close.assert_called_once_with()


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (429, "rate limit or quota"),
        (408, "generation timed out"),
        (504, "generation timed out"),
        (500, "API error"),
    ],
)
def test_mocked_api_errors_are_sanitized(code, expected):
    mock_client = Mock()
    mock_client.interactions.create.side_effect = errors.APIError(
        code, {"error": {"message": "test-only sensitive provider detail"}}
    )
    with patch("patchpilot.providers.gemini_provider.genai.Client", return_value=mock_client):
        with pytest.raises(RepairProviderError, match=expected) as exc_info:
            GeminiProvider(_settings()).generate_repair("source", "expected")
    assert "sensitive provider detail" not in str(exc_info.value)
