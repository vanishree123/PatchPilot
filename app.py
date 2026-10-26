"""Streamlit dashboard for PatchPilot's local, predefined Slice 1 demo."""

from __future__ import annotations

import streamlit as st

from patchpilot.config import load_settings
from patchpilot.workflow import DemoRunResult, retry_predefined, run_demo


st.set_page_config(page_title="PatchPilot", page_icon="🛠️", layout="wide")
st.title("PatchPilot — AI-Powered Python Bug Repair")
st.caption("Find, fix, and verify Python bugs in a controlled workspace.")

st.info(
    "Gemini is used when configured. If no repair is returned, PatchPilot shows "
    "the reason and waits for you to choose the predefined repair."
)
st.info(
    "A passing targeted test verifies this example only. It does not prove that "
    "all cases work or that the patch is universally correct or secure."
)

left, right = st.columns([1, 1])
with left:
    st.subheader("Demo bug: discount applied twice")
    st.write("A shop offers a 10% discount, but the function subtracts it twice.")
    st.code(
        """def apply_discount(price):
    discount = price * 0.10
    return price - discount - discount  # Bug: discount applied twice""",
        language="python",
    )
    example_metrics = st.columns(3)
    example_metrics[0].metric("Input", "100")
    example_metrics[1].metric("Expected", "90")
    example_metrics[2].metric("Buggy result", "80")

with right:
    st.subheader("Repair workflow")
    st.write("1. Baseline Test → 2. Analyze Bug → 3. Propose Repair")
    st.write("4. Validate Patch → 5. Apply to Demo Copy → 6. Verify with Tests")
    run_col, reset_col = st.columns(2)
    with run_col:
        run_clicked = st.button(
            "Repair Demo Bug", type="primary", use_container_width=True
        )
    with reset_col:
        reset_clicked = st.button("Reset Demo", use_container_width=True)

if reset_clicked:
    st.session_state.pop("patchpilot_run", None)
    st.rerun()

if run_clicked:
    try:
        settings = load_settings()
        with st.spinner("Running the fixed test in fresh demo copies…"):
            st.session_state["patchpilot_run"] = run_demo(settings)
    except Exception as exc:  # Show operational errors without secrets or tracebacks.
        st.session_state.pop("patchpilot_run", None)
        st.error(f"The demo stopped safely: {exc}")

result: DemoRunResult | None = st.session_state.get("patchpilot_run")
if result is not None:
    if result.can_retry_predefined:
        if st.button("Try Predefined Demo Repair", type="secondary"):
            try:
                settings = load_settings()
                with st.spinner("Applying the predefined repair to a fresh demo copy…"):
                    st.session_state["patchpilot_run"] = retry_predefined(
                        settings, result
                    )
                st.rerun()
            except Exception as exc:
                st.error(f"The predefined retry stopped safely: {exc}")

    result = st.session_state.get("patchpilot_run")
    st.divider()
    st.subheader("Results")
    baseline_text = (
        "Baseline failed as expected"
        if result.baseline.status == "failed"
        else f"Baseline {result.baseline.status}"
    )
    validation_status = (
        "Patch rejected"
        if result.patch_rejected
        else "Not run; no AI repair returned"
        if result.latest_attempt.provenance == "unavailable"
        else "Patch passed"
        if result.validation_message == "Function syntax and patch boundaries passed validation."
        else "Validation or application failed"
    )
    applied_status = "Applied to demo copy" if result.function_source else "Not applied"
    test_status = {
        "passed": "Targeted test passed",
        "failed": "Targeted test failed",
        "timed_out": "Targeted test timed out",
        "not_run": "Targeted test not run",
    }.get(result.repair_test.status, f"Targeted test: {result.repair_test.status}")
    stages = [
        ("Baseline Test", baseline_text),
        ("Analyze Bug", "Bug identified"),
        ("Propose Repair", result.repair_label),
        ("Validate Patch", validation_status),
        ("Apply to Demo Copy", applied_status),
        ("Verify with Tests", test_status),
    ]
    for row_start in (0, 3):
        columns = st.columns(3)
        for column, (stage, status) in zip(columns, stages[row_start : row_start + 3]):
            with column:
                with st.container(border=True):
                    st.caption(stage)
                    st.markdown(f"**{status}**")

    baseline_col, repair_col = st.columns(2)
    with baseline_col:
        st.markdown("#### Original failure")
        if result.baseline.status == "failed":
            st.warning("Baseline Test Failed: the buggy function returns 80; expected 90.")
        elif result.baseline.status == "timed_out":
            st.error("Baseline test timed out. This is not a pass.")
        else:
            st.error(f"Baseline test result: {result.baseline.status}")
        st.code(
            result.baseline.stdout or result.baseline.stderr or "No test output captured.",
            language="text",
        )

    with repair_col:
        st.markdown("#### Proposed repair")
        st.warning(result.repair_label)
        st.caption(result.repair_reason)
        if result.function_source is not None:
            st.code(result.function_source, language="python")
        elif result.patch_rejected:
            st.info("No repair was applied because the returned candidate failed validation.")
        else:
            st.info("No repair candidate was returned. Choose the predefined repair below to continue.")
        if result.explanation:
            st.write(result.explanation)

    st.markdown("#### Patch validation")
    if result.patch_rejected:
        st.error(result.validation_message)
    elif result.latest_attempt.provenance == "unavailable":
        st.info("Patch validation was not run because Gemini returned no candidate.")
    elif result.validation_message == "Function syntax and patch boundaries passed validation.":
        st.success(result.validation_message)
    else:
        st.error(result.validation_message)
    st.markdown("#### Original source")
    if result.original_preserved:
        st.success("Original source remained unchanged (SHA-256 matched).")
    else:
        st.error(
            "Source-preservation failure: the original fixture did not remain "
            "unchanged during this workflow. No attempt can be reported as successful."
        )
    st.caption(f"Demo workspace: `{result.workspace_id}`")
    st.caption(f"Original SHA-256 before: `{result.original_hash_before}`")
    st.caption(f"Original SHA-256 after:  `{result.original_hash_after}`")

    st.markdown("#### Final targeted test")
    if result.patch_rejected:
        st.error("Targeted test not run because the AI patch was rejected before application.")
    elif result.repair_test.status == "not_run":
        if result.latest_attempt.provenance == "unavailable":
            st.warning("Targeted test was not run because Gemini returned no repair candidate.")
        else:
            st.error("Targeted test was not run because the patch could not be safely applied.")
    elif result.successful:
        st.success("Targeted test passed. This is evidence for this example, not proof of universal correctness or security.")
    elif result.repair_test.status == "passed":
        st.error("Targeted test passed, but the baseline or source-preservation checks failed; the workflow is not successful.")
    elif result.repair_test.status == "timed_out":
        st.error(f"{result.repair_label} verification timed out. It is not a successful repair.")
    else:
        st.error(f"{result.repair_label} verification failed. This attempt is not successful.")
    st.code(
        result.repair_test.stdout or result.repair_test.stderr or "No test output captured.",
        language="text",
    )

    st.markdown("#### Attempt history (this workflow only)")
    for index, attempt in enumerate(result.attempts, start=1):
        with st.expander(f"Attempt {index}: {attempt.repair_label}", expanded=True):
            st.caption(attempt.repair_reason)
            st.write(f"**Provenance:** `{attempt.provenance}`")
            if attempt.function_source:
                st.code(attempt.function_source, language="python")
            st.write(f"**Patch validation:** {attempt.validation_message}")
            st.write(f"**Targeted test:** {attempt.repair_test.status}")
            if attempt.repair_test.stdout or attempt.repair_test.stderr:
                st.code(
                    attempt.repair_test.stdout or attempt.repair_test.stderr,
                    language="text",
                )
            st.caption(f"Workspace: `{attempt.workspace_id}`")
            st.caption(f"Original SHA-256: `{attempt.original_hash_before}` → `{attempt.original_hash_after}`")
            if not attempt.original_preserved:
                st.error(
                    "Source-preservation failure for this attempt; it cannot be "
                    "reported as successful."
                )

st.caption("Patch validation checks the allowed syntax and destination; a test pass verifies only this targeted example.")
