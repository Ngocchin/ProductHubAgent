import asyncio

import main
from agents.product_hub import ProductHubUnavailable
from agents.telegram_release import TelegramUnavailable


def test_run_writes_blocked_report_when_sources_are_unavailable(monkeypatch, tmp_path):
    written = {}

    class MissingProductHub:
        async def collect(self):
            raise ProductHubUnavailable("CHƯA THỂ XÁC MINH Product Hub")

    class MissingTelegram:
        async def collect(self):
            raise TelegramUnavailable("CHƯA THỂ XÁC MINH Telegram")

    class Report:
        def __init__(self, _directory):
            pass

        def render(self, cards, releases, today, blockers, changes=None):
            return "blocked report", {"date": today.isoformat(), "blockers": blockers}

        def write(self, markdown, payload):
            written.update(markdown=markdown, payload=payload)

    class History:
        def __init__(self, _path):
            pass

        def previous(self):
            return None

        def diff(self, _payload):
            raise AssertionError("partial collection must not be compared to history")

        def save(self, _date, _payload):
            raise AssertionError("partial collection must not replace history")

    monkeypatch.setattr(main, "ProductHubAgent", MissingProductHub)
    monkeypatch.setattr(main, "TelegramReleaseAgent", MissingTelegram)
    monkeypatch.setattr(main, "QAReportAgent", Report)
    monkeypatch.setattr(main, "HistoryStore", History)
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("HISTORY_PATH", str(tmp_path / "history.json"))

    assert asyncio.run(main.run()) == 1
    assert written["markdown"] == "blocked report"
    assert len(written["payload"]["blockers"]) == 2
    assert written["payload"]["processed_release_ids"] == []
