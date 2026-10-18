"""Validation for user-exported, read-only Chrome extension snapshots."""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse


class ProductHubSnapshotError(ValueError):
    pass


def validate_snapshot(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProductHubSnapshotError("JSON không hợp lệ.") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ProductHubSnapshotError("Không đúng định dạng snapshot Product Hub được hỗ trợ.")
    parsed = urlparse(str(data.get("board_url", "")))
    if parsed.scheme != "https" or parsed.hostname != "product-hub.vuatho.com" or not parsed.path.startswith("/board"):
        raise ProductHubSnapshotError("Snapshot không được xuất từ Product Hub board hợp lệ.")
    if not isinstance(data.get("generated_at"), str) or not data["generated_at"]:
        raise ProductHubSnapshotError("Snapshot thiếu thời điểm đồng bộ.")
    columns = data.get("columns")
    if not isinstance(columns, list) or not {"Ready for QA", "Verifying"}.issubset(set(columns)):
        raise ProductHubSnapshotError("Snapshot chưa xác minh đủ hai cột Ready for QA và Verifying.")
    cards = data.get("cards")
    if not isinstance(cards, list):
        raise ProductHubSnapshotError("Snapshot thiếu danh sách card.")
    for card in cards:
        if not isinstance(card, dict):
            raise ProductHubSnapshotError("Card trong snapshot không hợp lệ.")
        if card.get("status") not in {"Ready for QA", "Verifying"} or card.get("qa") != "Chin":
            raise ProductHubSnapshotError("Snapshot chứa card ngoài hai cột cho phép hoặc QA không phải Chin.")
        if not isinstance(card.get("id"), str) or not re.fullmatch(r"VT-[A-Z0-9]+-\d+", card["id"]):
            raise ProductHubSnapshotError("Card thiếu mã Product Hub hợp lệ.")
        if not isinstance(card.get("title"), str):
            raise ProductHubSnapshotError("Card thiếu tiêu đề.")
    return data
