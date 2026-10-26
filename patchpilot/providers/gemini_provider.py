"""Gemini Interactions adapter. This module never executes model output."""

from __future__ import annotations

import httpx
from google import genai
from google.genai import errors, types

from ..config import Settings
from .base import RepairProviderError


REPAIR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "function_source": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["function_source", "explanation"],
    "additionalProperties": False,
}


class GeminiProvider:
    """Call the configured Gemini model with one fixed synthetic code example."""

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise RepairProviderError("GEMINI_API_KEY is not configured.")
        self._settings = settings

    def generate_repair(self, source: str, expected_behavior: str) -> str:
        prompt = (
            "Repair only the built-in Python discount function below. Return one "
            "replacement function named apply_discount(price) that meets the "
            "expected behavior. Do not include imports, extra functions, paths, "
            "commands, markdown, or execution instructions. The output schema "
            "contains only function_source and explanation.\n\n"
            f"Expected behavior: {expected_behavior}\n\n"
            "Original function:\n"
            f"{source}"
        )
        client = None
        try:
            client = genai.Client(
                api_key=self._settings.gemini_api_key,
                http_options=types.HttpOptions(
                    timeout=self._settings.gemini_request_timeout_ms,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            interaction = client.interactions.create(
                model=self._settings.gemini_model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": REPAIR_RESPONSE_SCHEMA,
                },
            )
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise RepairProviderError(
                "Gemini generation timed out before a repair was returned."
            ) from exc
        except errors.APIError as exc:
            if getattr(exc, "code", None) == 429:
                message = "Gemini rate limit or quota was reached (HTTP 429)."
            elif getattr(exc, "code", None) in (408, 504):
                message = "Gemini generation timed out before a repair was returned."
            else:
                message = "Gemini returned an API error before a repair was returned."
            raise RepairProviderError(message) from exc
        except Exception as exc:
            # Do not show/log exception text: SDK exceptions may contain request data.
            raise RepairProviderError(
                "Gemini request failed before a repair was returned."
            ) from exc
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    # Closing a local HTTP client must not mask the request outcome.
                    pass

        output_text = getattr(interaction, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise RepairProviderError(
                "Gemini returned no repair text; no patch was available."
            )
        return output_text
