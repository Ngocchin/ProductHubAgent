from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Comment:
    author: str
    body: str
    created_at: str | None = None


@dataclass
class Card:
    task_id: str
    title: str
    url: str
    status: str
    qa: str
    priority: str | None = None
    project: str | None = None
    module: str | None = None
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    documents: list[dict[str, str]] = field(default_factory=list)
    build: str | None = None
    discovered_at: str = field(default_factory=utc_now)
    updated_at: str | None = None
    source: str = "product_hub"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Release:
    release_id: str
    chat_id: int
    chat_title: str
    message_id: int
    date: str
    text: str
    version: str | None = None
    build: str | None = None
    platform: str | None = None
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestCase:
    test_case_id: str
    title: str
    preconditions: list[str]
    test_data: list[str]
    steps: list[str]
    expected_result: str
    priority: str
    source_requirement: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
