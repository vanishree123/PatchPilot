"""Choose a validated model repair or the approved no-patch fallback."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .patch_validator import PatchValidationError, RepairProposal, parse_proposal_json
from .providers.base import RepairProvider, RepairProviderError
from .providers.gemini_provider import GeminiProvider
from .workspace import ORIGINAL_FIXTURE


AI_GENERATED_LABEL = "AI-Generated"
AI_REJECTED_LABEL = "AI-Generated — Patch Rejected"
GEMINI_UNAVAILABLE_LABEL = "Gemini Unavailable — No Repair Returned"
GEMINI_NOT_CONFIGURED_LABEL = "Gemini Not Configured — No AI Attempt Made"
EXPECTED_BEHAVIOR = "For input price 100, apply one 10% discount and return 90."


@dataclass(frozen=True)
class RepairDecision:
    proposal: RepairProposal | None
    label: str
    reason: str
    rejected: bool = False


def request_repair(
    settings: Settings, provider: RepairProvider | None = None
) -> RepairDecision:
    """Return validated AI output or a distinct no-candidate/failure result."""
    if not settings.gemini_api_key:
        return RepairDecision(
            proposal=None,
            label=GEMINI_NOT_CONFIGURED_LABEL,
            reason=(
                "GEMINI_API_KEY is not configured. No AI request was made. "
                "Choose Try Predefined Demo Repair to run the built-in fallback."
            ),
        )

    selected_provider = provider or GeminiProvider(settings)
    source = ORIGINAL_FIXTURE.read_text(encoding="utf-8")
    try:
        raw_response = selected_provider.generate_repair(source, EXPECTED_BEHAVIOR)
    except RepairProviderError as exc:
        return RepairDecision(
            proposal=None,
            label=GEMINI_UNAVAILABLE_LABEL,
            reason=(
                f"{exc} No repair was returned. Choose Try Predefined Demo Repair "
                "to run the built-in fallback."
            ),
        )

    try:
        proposal = parse_proposal_json(raw_response)
    except PatchValidationError as exc:
        # A response string exists, so it is an AI attempt: never auto-fallback.
        detail = str(exc)
        if detail.startswith((
            "Invalid proposal JSON",
            "Proposal must contain exactly",
            "function_source and explanation must be strings",
            "Proposal is missing or too large",
        )):
            reason = f"Gemini response parsing failed: {detail}"
        else:
            reason = f"Gemini candidate failed strict patch validation: {detail}"
        return RepairDecision(
            proposal=None,
            label=AI_REJECTED_LABEL,
            reason=reason,
            rejected=True,
        )

    return RepairDecision(
        proposal=proposal,
        label=AI_GENERATED_LABEL,
        reason="Gemini returned a candidate that passed local patch validation.",
    )
