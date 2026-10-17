"""Optional AI adapter contract. Disabled unless explicitly configured."""
from __future__ import annotations
from typing import Protocol


class Analyzer(Protocol):
    def analyze_text(self, prompt: str) -> str: ...


class NoAIAdapter:
    def analyze_text(self, prompt: str) -> str:
        raise RuntimeError("AI adapter is not configured; use the deterministic QA fallback.")


def configured_adapter() -> Analyzer:
    # No outbound AI request is made by default. Configure an approved adapter in a later phase.
    return NoAIAdapter()
