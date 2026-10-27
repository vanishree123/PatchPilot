import json

import pytest

from patchpilot.config import Settings
from patchpilot.predefined_repair import PREDEFINED_FUNCTION, PREDEFINED_LABEL
from patchpilot.providers.base import RepairProviderError
from patchpilot.repair_service import (
    GEMINI_NOT_CONFIGURED_LABEL,
    GEMINI_UNAVAILABLE_LABEL,
)
from patchpilot.workflow import retry_predefined, run_demo
from patchpilot.workspace import ORIGINAL_FIXTURE, WORKSPACE_ROOT, sha256_file


def test_no_key_requires_explicit_predefined_repair_and_preserves_source():
    original_hash = sha256_file()
    settings = Settings("gemini", "gemini-3.8-flash", None, 90_000, 10)

    unavailable = run_demo(settings)

    assert unavailable.baseline.status == "failed"
    assert "80" in unavailable.baseline.stdout
    assert "90" in unavailable.baseline.stdout
    assert unavailable.repair_label == GEMINI_NOT_CONFIGURED_LABEL
    assert unavailable.repair_test.status == "not_run"
    assert unavailable.successful is False
    assert unavailable.can_retry_predefined is True
    result = retry_predefined(settings, unavailable)

    assert result.repair_label == "Predefined Demo Repair — Not AI-Generated"
    assert result.repair_test.status == "passed"
    assert result.successful is True
    assert len(result.attempts) == 2
    assert result.attempts[0].repair_label == GEMINI_NOT_CONFIGURED_LABEL
    assert result.original_hash_before == original_hash
    assert result.original_hash_after == original_hash
    assert result.original_preserved is True
    assert "No AI request was made" in result.attempts[0].repair_reason
    assert sha256_file() == original_hash


def test_mocked_rejected_provider_output_is_never_written_to_demo_copy():
    """Test-only fake provider returns hostile text; no real Gemini call is made."""

    class MockRepairProvider:
        def generate_repair(self, source, expected_behavior):
            assert "discount" in source
            assert "100" in expected_behavior
            return json.dumps(
                {
                    "function_source": (
                        "import pathlib\n"
                        "def apply_discount(price):\n"
                        "    return price * 0.9"
                    ),
                    "explanation": "Mocked invalid candidate for a rejection test.",
                }
            )

    settings = Settings("gemini", "mock-test-model", "test-only-mock-key", 1000, 10)
    original_source = ORIGINAL_FIXTURE.read_text(encoding="utf-8")

    result = run_demo(settings, provider=MockRepairProvider())

    demo_copy = WORKSPACE_ROOT / result.workspace_id / "buggy_discount.py"
    assert result.patch_rejected is True
    assert result.repair_label == "AI-Generated — Patch Rejected"
    assert result.repair_test.status == "not_run"
    assert result.successful is False
    assert demo_copy.read_text(encoding="utf-8") == original_source


class MockRepairProvider:
    """A test-only provider double. It is never wired into the dashboard."""

    def __init__(self, response):
        self.response = response

    def generate_repair(self, source, expected_behavior):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _ai_settings():
    return Settings("gemini", "mock-test-model", "test-only-mock-key", 1000, 10)


def _candidate(function_source):
    return json.dumps(
        {
            "function_source": function_source,
            "explanation": "Mocked test candidate; no live model was called.",
        }
    )


def test_mocked_provider_failure_before_response_offers_explicit_fallback():
    unavailable = run_demo(
        _ai_settings(),
        MockRepairProvider(RepairProviderError("Mocked unavailable provider.")),
    )

    assert len(unavailable.attempts) == 1
    assert unavailable.repair_label == GEMINI_UNAVAILABLE_LABEL
    assert unavailable.repair_test.status == "not_run"
    assert unavailable.successful is False
    assert unavailable.can_retry_predefined is True
    result = retry_predefined(_ai_settings(), unavailable)
    assert len(result.attempts) == 2
    assert result.attempts[0].repair_label == GEMINI_UNAVAILABLE_LABEL
    assert result.repair_label == PREDEFINED_LABEL
    assert result.repair_test.status == "passed"
    assert result.successful is True
    assert "Mocked unavailable" in result.attempts[0].repair_reason


@pytest.mark.parametrize(
    "raw_response",
    [
        "not JSON",
        _candidate("import os\ndef apply_discount(price):\n    return price * 0.9"),
    ],
    ids=["malformed-json", "rejected-ast"],
)
def test_mocked_rejected_candidate_requires_retry_and_stays_unwritten(raw_response):
    original_source = ORIGINAL_FIXTURE.read_text(encoding="utf-8")
    result = run_demo(_ai_settings(), MockRepairProvider(raw_response))

    assert result.patch_rejected is True
    assert result.can_retry_predefined is True
    assert result.repair_test.status == "not_run"
    assert result.successful is False
    assert (WORKSPACE_ROOT / result.workspace_id / "buggy_discount.py").read_text(
        encoding="utf-8"
    ) == original_source


def test_mocked_valid_ai_patch_that_fails_test_is_not_replaced_automatically():
    result = run_demo(
        _ai_settings(),
        MockRepairProvider(
            _candidate(
                "def apply_discount(price):\n    return price - price * 0.20"
            )
        ),
    )

    assert result.repair_label == "AI-Generated — Verification Failed"
    assert result.repair_test.status == "failed"
    assert "80" in result.repair_test.stdout
    assert "90" in result.repair_test.stdout
    assert result.can_retry_predefined is True
    assert result.successful is False
    assert len(result.attempts) == 1


def test_mocked_ai_failure_retry_uses_fresh_copy_and_preserves_history():
    ai_result = run_demo(
        _ai_settings(),
        MockRepairProvider(
            _candidate(
                "def apply_discount(price):\n    return price - price * 0.20"
            )
        ),
    )
    failed_attempt = ai_result.attempts[0]
    failed_workspace = WORKSPACE_ROOT / failed_attempt.workspace_id
    failed_copy_before_retry = (failed_workspace / "buggy_discount.py").read_text(
        encoding="utf-8"
    )

    retried = retry_predefined(_ai_settings(), ai_result)

    assert len(retried.attempts) == 2
    assert retried.attempts[0] == failed_attempt
    assert failed_attempt.repair_label == "AI-Generated — Verification Failed"
    assert failed_attempt.repair_test.status == "failed"
    assert (failed_workspace / "buggy_discount.py").read_text(
        encoding="utf-8"
    ) == failed_copy_before_retry
    retry_attempt = retried.attempts[1]
    assert retry_attempt.provenance == "predefined"
    assert retry_attempt.repair_label == PREDEFINED_LABEL
    assert retry_attempt.repair_test.status == "passed"
    assert retry_attempt.workspace_id != failed_attempt.workspace_id
    assert (
        WORKSPACE_ROOT / retry_attempt.workspace_id / "buggy_discount.py"
    ).read_text(encoding="utf-8") == PREDEFINED_FUNCTION + "\n"
    assert retried.successful is True
    assert retried.original_preserved is True


def test_mocked_rejected_patch_requires_and_records_explicit_predefined_retry():
    original_source = ORIGINAL_FIXTURE.read_text(encoding="utf-8")
    rejected = run_demo(
        _ai_settings(), MockRepairProvider("candidate was malformed JSON")
    )
    rejected_attempt = rejected.attempts[0]

    retried = retry_predefined(_ai_settings(), rejected)

    assert len(retried.attempts) == 2
    assert retried.attempts[0] == rejected_attempt
    assert rejected_attempt.patch_rejected is True
    assert rejected_attempt.repair_test.status == "not_run"
    assert "Invalid proposal JSON" in rejected_attempt.repair_reason
    assert retried.attempts[1].repair_label == PREDEFINED_LABEL
    assert retried.attempts[1].repair_test.status == "passed"
    assert retried.attempts[1].workspace_id != rejected_attempt.workspace_id
    assert (
        WORKSPACE_ROOT / rejected_attempt.workspace_id / "buggy_discount.py"
    ).read_text(encoding="utf-8") == original_source
    assert retried.successful is True


def test_mocked_ai_test_timeout_is_failed_then_fallback_retry_passes(monkeypatch):
    import patchpilot.workflow as workflow

    calls = iter(
        [
            workflow.RunResult("failed", 1, "actual 80 expected 90", ""),
            workflow.RunResult("timed_out", None, "still running", ""),
        ]
    )
    monkeypatch.setattr(workflow, "run_targeted_test", lambda *args: next(calls))
    result = run_demo(
        _ai_settings(),
        MockRepairProvider(
            _candidate("def apply_discount(price):\n    return price * 0.9")
        ),
    )

    assert result.repair_label == "AI-Generated — Verification Failed (Test Timed Out)"
    assert result.repair_test.status == "timed_out"
    assert result.successful is False
    assert result.can_retry_predefined is True
    monkeypatch.undo()

    retried = retry_predefined(_ai_settings(), result)
    assert len(retried.attempts) == 2
    assert retried.attempts[0].repair_test.status == "timed_out"
    assert retried.attempts[1].repair_test.status == "passed"
    assert retried.successful is True


def test_source_hash_mismatch_blocks_success(monkeypatch):
    import patchpilot.workflow as workflow

    monkeypatch.setattr(
        workflow,
        "verify_original_hash",
        lambda expected: (False, "changed-source-hash"),
    )
    result = run_demo(Settings("gemini", "mock-model", None, 1000, 10))

    assert result.repair_test.status == "not_run"
    assert result.original_preserved is False
    assert result.successful is False
    assert result.can_retry_predefined is False
    assert "Source-preservation failure" in result.validation_message


def test_retry_is_unavailable_for_verified_ai_candidate():
    result = run_demo(
        _ai_settings(),
        MockRepairProvider(
            _candidate("def apply_discount(price):\n    return price * 0.9")
        ),
    )

    assert result.repair_test.status == "passed"
    assert result.can_retry_predefined is False
    with pytest.raises(ValueError, match="Gemini is unavailable"):
        retry_predefined(_ai_settings(), result)
