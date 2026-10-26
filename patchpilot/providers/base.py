"""Provider-neutral types for obtaining a repair proposal."""

from __future__ import annotations

from typing import Protocol


class RepairProviderError(RuntimeError):
    """A provider could not return a repair candidate; message is safe to display."""


class RepairProvider(Protocol):
    def generate_repair(self, source: str, expected_behavior: str) -> str:
        """Return the model's raw JSON text, without interpreting or applying it."""
