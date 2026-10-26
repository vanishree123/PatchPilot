from pathlib import Path

from streamlit.testing.v1 import AppTest
from patchpilot.test_runner import RunResult
from patchpilot.workflow import DemoRunResult, RepairAttempt


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_dashboard_reports_no_key_then_runs_explicit_predefined_repair(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app = AppTest.from_file(APP, default_timeout=45).run()
    assert not app.exception
    assert any(button.label == "Repair Demo Bug" for button in app.button)

    app.button[0].click().run()

    assert not app.exception
    assert any("Gemini Not Configured" in item.value for item in app.warning)
    assert not any("Targeted test passed" in item.value for item in app.success)
    retry_button = next(
        button for button in app.button if button.label == "Try Predefined Demo Repair"
    )
    retry_button.click().run()

    assert not app.exception
    assert any("Targeted test passed" in item.value for item in app.success)
    assert any(
        "Predefined Demo Repair \u2014 Not AI-Generated" in item.value
        for item in app.warning
    )

    next(button for button in app.button if button.label == "Reset Demo").click().run()
    assert "patchpilot_run" not in app.session_state


def test_dashboard_retry_displays_both_attempts_then_reset_clears_history():
    """Use a synthetic failed record to exercise UI state; no model is called."""
    failed_attempt = RepairAttempt(
        provenance="ai_generated",
        repair_label="AI-Generated \u2014 Verification Failed",
        repair_reason="Mock-only fixture: the AI candidate's test failed.",
        explanation="Mocked candidate for UI state coverage.",
        function_source="def apply_discount(price):\n    return price * 0.8",
        validation_message="Function syntax and patch boundaries passed validation.",
        repair_test=RunResult("failed", 1, "assert 80 == 90", ""),
        original_hash_before="same-hash",
        original_hash_after="same-hash",
        original_preserved=True,
        workspace_id="mock-ai-workspace",
    )
    initial_result = DemoRunResult(
        baseline=RunResult("failed", 1, "actual 80 expected 90", ""),
        attempts=(failed_attempt,),
        original_hash_before="same-hash",
        original_hash_after="same-hash",
        original_preserved=True,
    )
    app = AppTest.from_file(APP, default_timeout=45).run()
    app.session_state["patchpilot_run"] = initial_result
    app.run()

    assert any(button.label == "Try Predefined Demo Repair" for button in app.button)
    retry_button = next(
        button for button in app.button if button.label == "Try Predefined Demo Repair"
    )
    retry_button.click().run()

    assert not app.exception
    assert any("Targeted test passed" in item.value for item in app.success)
    assert len(app.session_state["patchpilot_run"].attempts) == 2
    assert any("Attempt 1: AI-Generated" in item.label for item in app.expander)
    assert any("Attempt 2: Predefined Demo Repair" in item.label for item in app.expander)

    next(button for button in app.button if button.label == "Reset Demo").click().run()
    assert "patchpilot_run" not in app.session_state
