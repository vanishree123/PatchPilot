"""Unit tests use explicitly labeled local test doubles; they do not call Gemini."""

from patchpilot.config import Settings
from patchpilot.providers.base import RepairProviderError
from patchpilot.repair_service import (
    AI_REJECTED_LABEL,
    GEMINI_NOT_CONFIGURED_LABEL,
    GEMINI_UNAVAILABLE_LABEL,
    request_repair,
)


class MockProvider:
    """Test-only fake provider response; never used by the application UI."""

    def __init__(self, result):
        self.result = result

    def generate_repair(self, source, expected_behavior):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _settings(key="test-only-mock-key"):
    return Settings("gemini", "mock-test-model", key, 1000, 10)


def test_no_key_reports_unavailable_without_calling_a_provider():
    class ProviderMustNotRun:
        def generate_repair(self, source, expected_behavior):
            raise AssertionError("Provider must not be called without a key")

    decision = request_repair(_settings(key=None), ProviderMustNotRun())

    assert decision.label == GEMINI_NOT_CONFIGURED_LABEL
    assert decision.proposal is None
    assert "No AI request was made" in decision.reason
    assert "Try Predefined Demo Repair" in decision.reason


def test_mocked_pre_patch_provider_failure_offers_labeled_fallback():
    decision = request_repair(
        _settings(), MockProvider(RepairProviderError("Mocked timeout before response."))
    )

    assert decision.label == GEMINI_UNAVAILABLE_LABEL
    assert decision.proposal is None
    assert "Mocked timeout" in decision.reason
    assert "Try Predefined Demo Repair" in decision.reason


def test_mocked_returned_invalid_candidate_is_rejected_without_fallback():
    response = '{"function_source":"import os\\ndef apply_discount(price):\\n return price", "explanation":"Mocked invalid output."}'
    decision = request_repair(_settings(), MockProvider(response))

    assert decision.label == AI_REJECTED_LABEL
    assert decision.rejected is True
    assert decision.proposal is None
    assert "predefined" not in decision.reason.lower()


def test_mocked_malformed_json_is_labeled_as_response_parsing_failure():
    decision = request_repair(_settings(), MockProvider("not JSON"))

    assert decision.label == AI_REJECTED_LABEL
    assert decision.rejected is True
    assert decision.proposal is None
    assert "response parsing failed" in decision.reason.lower()
    assert "Try Predefined Demo Repair" not in decision.reason


def test_configured_dashboard_backend_selects_gemini_provider_without_network(monkeypatch):
    import patchpilot.repair_service as repair_service

    seen = {}

    class MockGeminiProvider:
        """Factory double that proves settings routing without an HTTP request."""

        def __init__(self, settings):
            seen["settings"] = settings

        def generate_repair(self, source, expected_behavior):
            seen["source"] = source
            seen["expected_behavior"] = expected_behavior
            return "mocked malformed response"

    configured = _settings()
    monkeypatch.setattr(repair_service, "GeminiProvider", MockGeminiProvider)

    decision = request_repair(configured)

    assert seen["settings"] is configured
    assert "apply_discount" in seen["source"]
    assert "100" in seen["expected_behavior"]
    assert decision.label == AI_REJECTED_LABEL
    assert decision.proposal is None
