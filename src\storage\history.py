from __future__ import annotations

import json
from pathlib import Path


class HistoryStore:
    """JSON history file committed alongside reports for durable Actions runs."""
    def __init__(self, path: str | Path = "reports/history.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def previous(self) -> dict | None:
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        return rows[max(rows)] if rows else None

    def save(self, run_date: str, payload: dict) -> None:
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        rows[run_date] = payload
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def diff(self, current: dict) -> dict:
        old = self.previous()
        if not old:
            return {"baseline": "none", "new": [c["task_id"] for c in current.get("cards", [])]}
        before = {c["task_id"]: c for c in old.get("cards", [])}
        after = {c["task_id"]: c for c in current.get("cards", [])}
        return {"new": sorted(after.keys() - before.keys()),
                "removed": sorted(before.keys() - after.keys()),
                "status_changed": sorted(k for k in before.keys() & after.keys() if before[k].get("status") != after[k].get("status")),
                "description_changed": sorted(k for k in before.keys() & after.keys() if before[k].get("description") != after[k].get("description"))}
