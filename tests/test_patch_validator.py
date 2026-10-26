import json

import pytest

from patchpilot.patch_validator import PatchValidationError, parse_proposal_json
from patchpilot.predefined_repair import predefined_proposal_json


def test_predefined_repair_matches_approved_json_and_ast_shape():
    proposal = parse_proposal_json(predefined_proposal_json())

    assert proposal.function_source == "def apply_discount(price):\n    return price - price * 0.10"
    assert "subtract" in proposal.explanation.lower()


@pytest.mark.parametrize(
    "payload",
    [
        '{"function_source": "def apply_discount(price): return price", "explanation": "ok", "path": "x"}',
        '{"function_source": "def apply_discount(price): return price", "explanation": "ok", "command": "whoami"}',
        '{"function_source": "def apply_discount(price): return price", "explanation": "ok", "explanation": "again"}',
        "```json\\n{}\\n```",
        json.dumps({"function_source": "import os\ndef apply_discount(price):\n return price", "explanation": "bad"}),
        json.dumps({"function_source": "def apply_discount(price):\n return open('x')", "explanation": "bad"}),
        json.dumps({"function_source": "def other(price):\n return price", "explanation": "bad"}),
        json.dumps({"function_source": "def apply_discount(price):\n price = 90\n return price", "explanation": "bad"}),
    ],
)
def test_validator_rejects_extra_json_or_disallowed_syntax(payload):
    with pytest.raises(PatchValidationError):
        parse_proposal_json(payload)
