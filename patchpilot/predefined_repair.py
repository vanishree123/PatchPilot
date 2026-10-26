"""The explicitly labeled repair for the one built-in discount fixture."""

import json


PREDEFINED_LABEL = "Predefined Demo Repair — Not AI-Generated"
PREDEFINED_FUNCTION = "def apply_discount(price):\n    return price - price * 0.10"
PREDEFINED_EXPLANATION = (
    "Subtract the 10% discount once so a price of 100 becomes 90."
)


def predefined_proposal_json() -> str:
    """Return the predefined proposal in the same strict JSON shape as the model."""
    return json.dumps(
        {
            "function_source": PREDEFINED_FUNCTION,
            "explanation": PREDEFINED_EXPLANATION,
        }
    )
