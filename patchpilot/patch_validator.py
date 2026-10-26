"""Strict JSON and syntax-tree allowlist for the built-in repair function."""

from __future__ import annotations

import ast
import json
import math
from dataclasses import dataclass
from pathlib import Path


MAX_JSON_CHARS = 8_000
MAX_FUNCTION_CHARS = 4_000
MAX_EXPLANATION_CHARS = 500


class PatchValidationError(ValueError):
    """Raised when a proposed repair is outside the approved small grammar."""


@dataclass(frozen=True)
class RepairProposal:
    function_source: str
    explanation: str


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PatchValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_proposal_json(raw_json: str) -> RepairProposal:
    if not isinstance(raw_json, str) or len(raw_json) > MAX_JSON_CHARS:
        raise PatchValidationError("Proposal is missing or too large")
    try:
        obj = json.loads(raw_json, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, PatchValidationError) as exc:
        raise PatchValidationError(f"Invalid proposal JSON: {exc}") from exc
    if not isinstance(obj, dict) or set(obj) != {"function_source", "explanation"}:
        raise PatchValidationError(
            "Proposal must contain exactly function_source and explanation"
        )
    source = obj["function_source"]
    explanation = obj["explanation"]
    if not isinstance(source, str) or not isinstance(explanation, str):
        raise PatchValidationError("function_source and explanation must be strings")
    if not source.strip() or len(source) > MAX_FUNCTION_CHARS:
        raise PatchValidationError("Function source is empty or too large")
    if not explanation.strip() or len(explanation) > MAX_EXPLANATION_CHARS:
        raise PatchValidationError("Explanation is empty or too large")
    proposal = RepairProposal(source.strip(), explanation.strip())
    validate_function_source(proposal.function_source)
    return proposal


def validate_function_source(source: str) -> ast.FunctionDef:
    """Accept only one apply_discount(price) function with a tiny arithmetic AST."""
    if not isinstance(source, str) or not source.strip():
        raise PatchValidationError("Function source is empty")
    if len(source) > MAX_FUNCTION_CHARS:
        raise PatchValidationError("Function source is too large")
    try:
        module = ast.parse(source)
    except SyntaxError as exc:
        raise PatchValidationError(f"Invalid Python syntax: {exc.msg}") from exc

    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef):
        raise PatchValidationError("Source must contain exactly one function definition")
    function = module.body[0]
    if function.name != "apply_discount":
        raise PatchValidationError("Only apply_discount may be defined")
    if (function.decorator_list or function.returns is not None
            or function.type_comment is not None
            or getattr(function, "type_params", [])):
        raise PatchValidationError("Decorators, annotations, and type parameters are not allowed")

    args = function.args
    if (args.posonlyargs or len(args.args) != 1 or args.args[0].arg != "price"
            or args.vararg is not None or args.kwonlyargs or args.kw_defaults
            or args.kwarg is not None or args.defaults):
        raise PatchValidationError("Function must take exactly one argument named price")
    if len(function.body) != 1 or not isinstance(function.body[0], ast.Return):
        raise PatchValidationError("Function body must contain exactly one return statement")
    returned = function.body[0]
    if returned.value is None:
        raise PatchValidationError("Return statement must return an arithmetic expression")

    allowed_nodes = (
        ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UAdd, ast.USub,
    )
    for node in ast.walk(returned.value):
        if not isinstance(node, allowed_nodes):
            raise PatchValidationError(f"Disallowed syntax node: {type(node).__name__}")
        if isinstance(node, ast.Name) and (node.id != "price" or not isinstance(node.ctx, ast.Load)):
            raise PatchValidationError("Only the read-only name price is allowed")
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PatchValidationError("Only integer or finite float constants are allowed")
            if isinstance(value, float) and not math.isfinite(value):
                raise PatchValidationError("Non-finite numeric constants are not allowed")
        if isinstance(node, ast.BinOp) and not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            raise PatchValidationError("Only addition, subtraction, multiplication, and division are allowed")
        if isinstance(node, ast.UnaryOp) and not isinstance(node.op, (ast.UAdd, ast.USub)):
            raise PatchValidationError("Only unary plus and minus are allowed")
    return function


def apply_proposal_to_workspace(proposal: RepairProposal, workspace: Path) -> Path:
    """Write a validated function only to buggy_discount.py inside an owned workspace."""
    validate_function_source(proposal.function_source)
    repository_root = Path(__file__).resolve().parents[1]
    runtime_root = (repository_root / "runtime" / "demo_workspaces").resolve()
    workspace_path = workspace.resolve(strict=True)
    if not workspace_path.is_relative_to(runtime_root):
        raise PatchValidationError("Demo workspace is outside the controlled workspace root")
    target = (workspace_path / "buggy_discount.py").resolve(strict=False)
    if target.parent != workspace_path or target.name != "buggy_discount.py":
        raise PatchValidationError("Repair target is outside the permitted demo file")
    target.write_text(proposal.function_source.rstrip() + "\n", encoding="utf-8")
    return target
