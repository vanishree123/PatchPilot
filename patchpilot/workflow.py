"""Repair orchestration with transient attempt history and explicit fallback retry."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .config import Settings
from .patch_validator import (
    PatchValidationError,
    RepairProposal,
    apply_proposal_to_workspace,
)
from .predefined_repair import PREDEFINED_LABEL, predefined_proposal_json
from .providers.base import RepairProvider
from .repair_service import (
    AI_GENERATED_LABEL,
    AI_REJECTED_LABEL,
    RepairDecision,
    request_repair,
)
from .test_runner import RunResult, run_targeted_test
from .workspace import (
    create_fresh_workspace,
    sha256_file,
    verify_original_hash,
)


@dataclass(frozen=True)
class RepairAttempt:
    provenance: str
    repair_label: str
    repair_reason: str
    explanation: str | None
    function_source: str | None
    validation_message: str
    repair_test: RunResult
    original_hash_before: str
    original_hash_after: str
    original_preserved: bool
    workspace_id: str
    patch_rejected: bool = False

    @property
    def successful(self) -> bool:
        return self.repair_test.status == "passed" and self.original_preserved

    @property
    def can_retry_predefined(self) -> bool:
        if self.provenance == "unavailable":
            return self.repair_test.status == "not_run" and not self.patch_rejected
        return self.provenance == "ai_generated" and (
            self.patch_rejected
            or self.repair_test.status in {"failed", "timed_out", "not_run"}
        )


@dataclass(frozen=True)
class DemoRunResult:
    baseline: RunResult
    attempts: tuple[RepairAttempt, ...]
    original_hash_before: str
    original_hash_after: str
    original_preserved: bool

    @property
    def latest_attempt(self) -> RepairAttempt:
        return self.attempts[-1]

    @property
    def repair_test(self) -> RunResult:
        return self.latest_attempt.repair_test

    @property
    def repair_label(self) -> str:
        return self.latest_attempt.repair_label

    @property
    def repair_reason(self) -> str:
        return self.latest_attempt.repair_reason

    @property
    def explanation(self) -> str | None:
        return self.latest_attempt.explanation

    @property
    def function_source(self) -> str | None:
        return self.latest_attempt.function_source

    @property
    def validation_message(self) -> str:
        return self.latest_attempt.validation_message

    @property
    def workspace_id(self) -> str:
        return self.latest_attempt.workspace_id

    @property
    def patch_rejected(self) -> bool:
        return self.latest_attempt.patch_rejected

    @property
    def can_retry_predefined(self) -> bool:
        return self.original_preserved and self.latest_attempt.can_retry_predefined

    @property
    def successful(self) -> bool:
        expected_baseline = (
            self.baseline.status == "failed"
            and "80" in self.baseline.stdout
            and "90" in self.baseline.stdout
        )
        return (
            expected_baseline
            and bool(self.attempts)
            and self.latest_attempt.successful
            and self.original_preserved
        )


def _make_attempt(
    settings: Settings,
    decision: RepairDecision,
    original_hash_before: str,
) -> RepairAttempt:
    """Apply one proposal, verify it, and record actual outcomes plus source hash."""
    if decision.label.startswith("AI-Generated"):
        provenance = "ai_generated"
    elif decision.label.startswith("Gemini "):
        provenance = "unavailable"
    else:
        provenance = "predefined"
    workspace = create_fresh_workspace()
    repair_test = RunResult("not_run", None, "", "")
    function_source: str | None = None
    explanation: str | None = None
    patch_rejected = decision.rejected
    validation_message = (
        decision.reason
        if patch_rejected or decision.proposal is None
        else ""
    )

    if not patch_rejected and decision.proposal is not None:
        try:
            apply_proposal_to_workspace(decision.proposal, workspace.path)
        except PatchValidationError as exc:
            patch_rejected = provenance == "ai_generated"
            label = AI_REJECTED_LABEL if patch_rejected else decision.label
            decision = replace(
                decision,
                label=label,
                reason=f"Patch boundary rejected the candidate: {exc}",
                rejected=patch_rejected,
            )
            validation_message = decision.reason
        except OSError as exc:
            decision = replace(
                decision,
                label=(
                    "AI-Generated — Verification Failed"
                    if provenance == "ai_generated"
                    else decision.label
                ),
                reason=f"The validated patch could not be applied to its demo copy: {exc}",
            )
            validation_message = decision.reason
        else:
            function_source = decision.proposal.function_source
            explanation = decision.proposal.explanation
            validation_message = "Function syntax and patch boundaries passed validation."
            repair_test = run_targeted_test(
                workspace.path, settings.test_timeout_seconds
            )
            if provenance == "ai_generated" and repair_test.status != "passed":
                if repair_test.status == "timed_out":
                    decision = replace(
                        decision,
                        label="AI-Generated — Verification Failed (Test Timed Out)",
                        reason=(
                            "The AI patch passed boundary validation, but the "
                            "targeted test timed out."
                        ),
                    )
                elif repair_test.status == "failed":
                    decision = replace(
                        decision,
                        label="AI-Generated — Verification Failed",
                        reason=(
                            "The AI patch passed boundary validation, but the "
                            "targeted test failed. Its actual output is retained."
                        ),
                    )

    original_preserved, original_hash_after = verify_original_hash(
        original_hash_before
    )
    if not original_preserved:
        validation_message = (
            "Source-preservation failure: the original fixture SHA-256 changed. "
            "This attempt cannot be reported as successful."
        )

    return RepairAttempt(
        provenance=provenance,
        repair_label=decision.label,
        repair_reason=decision.reason,
        explanation=explanation,
        function_source=function_source,
        validation_message=validation_message,
        repair_test=repair_test,
        original_hash_before=original_hash_before,
        original_hash_after=original_hash_after,
        original_preserved=original_preserved,
        workspace_id=workspace.workspace_id,
        patch_rejected=patch_rejected,
    )


def run_demo(
    settings: Settings, provider: RepairProvider | None = None
) -> DemoRunResult:
    """Run the fixed baseline and first AI or predefined attempt."""
    original_hash_before = sha256_file()
    baseline_workspace = create_fresh_workspace()
    baseline = run_targeted_test(
        baseline_workspace.path, settings.test_timeout_seconds
    )
    decision = request_repair(settings, provider)
    attempt = _make_attempt(settings, decision, original_hash_before)
    return DemoRunResult(
        baseline=baseline,
        attempts=(attempt,),
        original_hash_before=original_hash_before,
        original_hash_after=attempt.original_hash_after,
        original_preserved=attempt.original_preserved,
    )


def retry_predefined(settings: Settings, result: DemoRunResult) -> DemoRunResult:
    """Run a user-selected fallback on a new copy while retaining prior attempts."""
    if not result.can_retry_predefined:
        raise ValueError(
            "Predefined retry is available only after Gemini is unavailable "
            "or a returned AI repair fails"
        )
    hash_before = sha256_file()
    proposal_json = predefined_proposal_json()
    from .patch_validator import parse_proposal_json

    decision = RepairDecision(
        proposal=parse_proposal_json(proposal_json),
        label=PREDEFINED_LABEL,
        reason=(
            "User selected Try Predefined Demo Repair after Gemini was unavailable "
            "or the returned AI attempt failed."
        ),
    )
    retry_attempt = _make_attempt(settings, decision, hash_before)
    return DemoRunResult(
        baseline=result.baseline,
        attempts=result.attempts + (retry_attempt,),
        original_hash_before=result.original_hash_before,
        original_hash_after=retry_attempt.original_hash_after,
        original_preserved=(
            result.original_preserved and retry_attempt.original_preserved
        ),
    )
